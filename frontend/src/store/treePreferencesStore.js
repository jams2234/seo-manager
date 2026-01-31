/**
 * Tree Preferences Store
 * Manages all tree visualization preferences with automatic localStorage persistence
 *
 * Replaces 7 separate localStorage + useEffect combinations with a single Zustand store
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useTreePreferencesStore = create(
  persist(
    (set) => ({
      // Edit mode
      editMode: false,
      setEditMode: (editMode) => set({ editMode }),

      // Layout settings
      useAutoLayout: true, // Default: auto-layout enabled
      setUseAutoLayout: (useAutoLayout) => set({ useAutoLayout }),

      layoutDirection: 'TB', // 'TB' (top-bottom) or 'LR' (left-right)
      setLayoutDirection: (layoutDirection) => set({ layoutDirection }),

      // Filter settings
      filterMode: 'all', // 'all', 'subdomains', 'pages', etc.
      setFilterMode: (filterMode) => set({ filterMode }),

      showHiddenNodes: false,
      setShowHiddenNodes: (showHiddenNodes) => set({ showHiddenNodes }),

      // Auto-connect feature
      autoConnectEnabled: true, // Default: enabled
      setAutoConnectEnabled: (autoConnectEnabled) => set({ autoConnectEnabled }),

      // Edge style configuration
      edgeStyle: {
        type: 'smoothstep', // 'smoothstep', 'step', 'straight', 'bezier'
        animated: false,
        style: { stroke: '#b1b1b7', strokeWidth: 2 }
      },
      setEdgeStyle: (edgeStyle) => set({ edgeStyle }),

      // Reset all preferences to defaults
      resetPreferences: () => set({
        editMode: false,
        useAutoLayout: true,
        layoutDirection: 'TB',
        filterMode: 'all',
        showHiddenNodes: false,
        autoConnectEnabled: true,
        edgeStyle: {
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#b1b1b7', strokeWidth: 2 }
        }
      }),
    }),
    {
      name: 'tree-preferences', // localStorage key
      version: 1, // For future migrations

      // Partial persistence (exclude functions)
      partialize: (state) => ({
        editMode: state.editMode,
        useAutoLayout: state.useAutoLayout,
        layoutDirection: state.layoutDirection,
        filterMode: state.filterMode,
        showHiddenNodes: state.showHiddenNodes,
        autoConnectEnabled: state.autoConnectEnabled,
        edgeStyle: state.edgeStyle,
      }),
    }
  )
);

export default useTreePreferencesStore;
