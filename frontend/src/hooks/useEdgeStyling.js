/**
 * useEdgeStyling Hook
 * Transforms edges with styling based on depth, groups, and edge style settings
 */
import { useMemo } from 'react';
import { MarkerType } from 'reactflow';
import { getDepthColor } from '../constants/themeColors';

/**
 * Transform backend edges to React Flow edges with styling
 *
 * @param {Array} edges - Raw edges from backend
 * @param {Array} styledNodes - Already styled nodes (for lookup)
 * @param {Array} rawNodes - Original nodes from backend (for metadata)
 * @param {Object} edgeStyle - Edge style configuration
 * @returns {Array} Styled React Flow edges
 */
const useEdgeStyling = (edges, styledNodes, rawNodes, edgeStyle) => {
  return useMemo(() => {
    if (!edges || edges.length === 0 || !styledNodes || !rawNodes) {
      return [];
    }

    // Create lookup maps
    const nodeMap = {};
    rawNodes.forEach((node) => {
      nodeMap[String(node.id)] = node;
    });

    return edges.map((edge) => {
      const targetNode = nodeMap[String(edge.target)];
      const depthLevel = targetNode?.depth_level || 0;
      const isSubdomain = targetNode?.is_subdomain || false;

      // Determine edge color
      let edgeColor = getDepthColor(depthLevel);
      if (edgeStyle.useGroupColors && targetNode?.group?.color) {
        edgeColor = targetNode.group.color;
      }

      // Calculate stroke width
      let strokeWidth = 2;
      switch (edgeStyle.strokeWidth) {
        case 'thin':
          strokeWidth = 1;
          break;
        case 'medium':
          strokeWidth = 2;
          break;
        case 'thick':
          strokeWidth = 3;
          break;
        case 'auto':
        default:
          strokeWidth = isSubdomain ? 3 : 2;
          break;
      }

      return {
        id: `e${edge.source}-${edge.target}`,
        source: String(edge.source),
        target: String(edge.target),
        type: 'smoothstep',
        animated: edgeStyle.animated || false,
        style: {
          stroke: edgeColor,
          strokeWidth: strokeWidth,
          strokeDasharray: isSubdomain ? '0' : '5, 5',
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: strokeWidth * 8,
          height: strokeWidth * 8,
          color: edgeColor,
        },
        label: edgeStyle.showLabels && isSubdomain ? '🌐' : '',
        labelStyle: {
          fontSize: 12,
          fill: edgeColor,
        },
        labelBgStyle: {
          fill: 'white',
          fillOpacity: 0.9,
        },
      };
    });
  }, [edges, styledNodes, rawNodes, edgeStyle]);
};

export default useEdgeStyling;
