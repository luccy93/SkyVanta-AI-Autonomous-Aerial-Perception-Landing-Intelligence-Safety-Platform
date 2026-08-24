"""Coordinate frame graph, transform registry, and shortest-path SE(3) composition."""

from collections import deque
from typing import Dict, List, Optional, Set, Tuple, Union
import numpy as np

from skyvanta.core.exceptions import DisconnectedFrameError, FrameError, TransformLookupError
from skyvanta.core.logging import get_logger
from skyvanta.core.types import FrameId, Pose6D, SpatialLocalizationResult, SpatialUncertainty
from skyvanta.spatial.frames import STANDARD_FRAMES, FrameDefinition
from skyvanta.spatial.se3 import SE3Transform

logger = get_logger("skyvanta.spatial.frame_graph")


class FrameGraph:
    """Manages coordinate frames and computes chained SE(3) spatial transformations."""

    def __init__(self):
        # Maps (target_frame, source_frame) -> SE3Transform (T_target_source)
        self._transforms: Dict[Tuple[FrameId, FrameId], SE3Transform] = {}
        # Known registered frame metadata
        self._frames: Dict[FrameId, FrameDefinition] = dict(STANDARD_FRAMES)

    def register_frame(self, frame_def: FrameDefinition) -> None:
        """Registers metadata for a new or custom coordinate frame."""
        self._frames[frame_def.frame_id] = frame_def

    def add_transform(self, transform: SE3Transform) -> None:
        """Registers or updates a directed SE(3) transform T_target_source in the graph."""
        src = transform.source_frame
        tgt = transform.target_frame

        if src == tgt:
            raise FrameError(f"Cannot register transform with identical source and target frame: {src}")

        # Store directed transform: T_tgt_src maps p_src -> p_tgt
        self._transforms[(tgt, src)] = transform
        logger.debug("Registered transform T_%s_%s (static=%s)", tgt.value, src.value, transform.is_static)

    def has_direct_transform(self, source_frame: Union[FrameId, str], target_frame: Union[FrameId, str]) -> bool:
        """Checks if a direct or immediately invertible transform exists between two frames."""
        src = FrameId(source_frame) if isinstance(source_frame, str) else source_frame
        tgt = FrameId(target_frame) if isinstance(target_frame, str) else target_frame
        return (tgt, src) in self._transforms or (src, tgt) in self._transforms

    def clear(self) -> None:
        """Clears all dynamic and static registered transforms."""
        self._transforms.clear()

    def find_path(self, source_frame: FrameId, target_frame: FrameId) -> List[Tuple[FrameId, FrameId, bool]]:
        """Finds the shortest sequence of frame hops from source_frame to target_frame using BFS.

        Returns:
            List of tuples: (u, v, is_forward) where:
            - is_forward is True if direct transform T_v_u exists in graph.
            - is_forward is False if reverse transform T_u_v exists and must be inverted.
        """
        if source_frame == target_frame:
            return []

        # Build adjacency list of available edges
        adjacency: Dict[FrameId, List[FrameId]] = {}
        for (tgt, src) in self._transforms.keys():
            adjacency.setdefault(src, []).append(tgt)   # Forward edge: T_tgt_src
            adjacency.setdefault(tgt, []).append(src)   # Reverse edge: T_src_tgt^(-1)

        if source_frame not in adjacency:
            raise DisconnectedFrameError(
                f"Source frame '{source_frame.value}' has no registered transforms in the frame graph"
            )
        if target_frame not in adjacency:
            raise DisconnectedFrameError(
                f"Target frame '{target_frame.value}' has no registered transforms in the frame graph"
            )

        # BFS for shortest path
        queue = deque([[source_frame]])
        visited: Set[FrameId] = {source_frame}
        path_nodes: Optional[List[FrameId]] = None

        while queue:
            current_path = queue.popleft()
            node = current_path[-1]

            if node == target_frame:
                path_nodes = current_path
                break

            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(current_path + [neighbor])

        if path_nodes is None:
            raise DisconnectedFrameError(
                f"No connected transform path exists between '{source_frame.value}' and '{target_frame.value}'"
            )

        # Convert node path to edge list with direction
        edges: List[Tuple[FrameId, FrameId, bool]] = []
        for i in range(len(path_nodes) - 1):
            u = path_nodes[i]
            v = path_nodes[i + 1]
            if (v, u) in self._transforms:
                edges.append((u, v, True))
            elif (u, v) in self._transforms:
                edges.append((u, v, False))
            else:
                raise DisconnectedFrameError(f"Missing edge between '{u.value}' and '{v.value}'")

        return edges

    def lookup_transform(
        self,
        source_frame: Union[FrameId, str],
        target_frame: Union[FrameId, str],
        timestamp_sec: Optional[float] = None,
        max_age_sec: Optional[float] = None,
    ) -> SE3Transform:
        """Finds and composes the complete SE(3) transform T_target_source to transform points/poses from source to target.

        Args:
            source_frame: Origin coordinate frame.
            target_frame: Destination coordinate frame.
            timestamp_sec: Optional timestamp for dynamic transform validation.
            max_age_sec: Maximum allowable age for dynamic transforms.

        Returns:
            Composed SE3Transform T_target_source.
        """
        src = FrameId(source_frame) if isinstance(source_frame, str) else source_frame
        tgt = FrameId(target_frame) if isinstance(target_frame, str) else target_frame

        if src == tgt:
            return SE3Transform.identity(src)

        edges = self.find_path(src, tgt)

        # Compose along the path: T_v_u = T_tgt_... * T_..._src
        composed_transform: Optional[SE3Transform] = None

        for u, v, is_forward in edges:
            if is_forward:
                step_transform = self._transforms[(v, u)]
            else:
                step_transform = self._transforms[(u, v)].inverse()

            # Age validation for dynamic transforms
            if not step_transform.is_static and timestamp_sec is not None and max_age_sec is not None:
                age = abs(timestamp_sec - step_transform.timestamp_sec)
                if age > max_age_sec:
                    raise TransformLookupError(
                        f"Transform T_{v.value}_{u.value} is stale (age {age:.3f}s > {max_age_sec:.3f}s)"
                    )

            if composed_transform is None:
                composed_transform = step_transform
            else:
                # Compose: T_v_start = T_v_u * T_u_start
                composed_transform = step_transform.compose(composed_transform)

        if composed_transform is None:
            raise DisconnectedFrameError(f"Could not compute transform from {src.value} to {tgt.value}")

        return composed_transform

    def transform_pose(
        self,
        pose: Pose6D,
        source_frame: Union[FrameId, str],
        target_frame: Union[FrameId, str],
        timestamp_sec: Optional[float] = None,
    ) -> SpatialLocalizationResult:
        """Transforms a 6-DoF pose from source_frame into target_frame."""
        src = FrameId(source_frame) if isinstance(source_frame, str) else source_frame
        tgt = FrameId(target_frame) if isinstance(target_frame, str) else target_frame
        t_sec = timestamp_sec if timestamp_sec is not None else pose.timestamp_sec

        try:
            transform = self.lookup_transform(src, tgt, timestamp_sec=t_sec)
            transformed_pose = transform.transform_pose(pose, new_target_frame=tgt)
            edges = self.find_path(src, tgt)
            chain_str = [src.value] + [e[1].value for e in edges]

            is_world = (tgt == FrameId.WORLD or src == FrameId.WORLD)

            return SpatialLocalizationResult(
                target_id=pose.target_id,
                source_frame=src,
                target_frame=tgt,
                pose=transformed_pose,
                homogeneous_matrix=transform.to_matrix().tolist(),
                timestamp_sec=t_sec,
                transform_chain=chain_str,
                is_valid=True,
                is_world_relative=is_world,
                failure_reason=None,
                quality_metadata={"reprojection_error_rms": pose.reprojection_error_rms, "quality": pose.pose_quality},
            )
        except Exception as e:
            logger.warning("Failed to transform pose from %s to %s: %s", src.value, tgt.value, e)
            reason = str(e)
            if tgt == FrameId.WORLD or src == FrameId.WORLD:
                reason = "WORLD frame reference is unavailable (no GPS, SLAM, or external visual odometry registered)"
            return SpatialLocalizationResult(
                target_id=pose.target_id,
                source_frame=src,
                target_frame=tgt,
                pose=None,
                timestamp_sec=t_sec,
                is_valid=False,
                is_world_relative=False,
                failure_reason=reason,
            )


    def transform_point(
        self,
        point_3d: Union[Tuple[float, float, float], List[float], np.ndarray],
        source_frame: Union[FrameId, str],
        target_frame: Union[FrameId, str],
    ) -> np.ndarray:
        """Transforms a 3D point from source_frame into target_frame."""
        transform = self.lookup_transform(source_frame, target_frame)
        return transform.transform_point(point_3d)
