/**
 * Workspace Store
 * Zustand store for managing tree workspace state
 */
import { create } from 'zustand';
import { workspaceService } from '../services/workspaceService';
import { domainService } from '../services/domainService';

const useWorkspaceStore = create((set, get) => ({
  // ==========================================================================
  // State
  // ==========================================================================

  // Current workspace
  workspace: null,
  workspaceLoading: false,
  workspaceError: null,

  // Available workspaces list
  workspaces: [],
  workspacesLoading: false,

  // Active tab's tree data (loaded from domain)
  activeTabTreeData: null,
  treeDataLoading: false,

  // Local tab states (viewport, positions, etc.) - synced to server periodically
  tabLocalStates: {}, // { [tabId]: { viewport, draggedPositions, hasUnsavedChanges } }

  // ==========================================================================
  // Workspace Actions
  // ==========================================================================

  /**
   * Fetch workspace list
   */
  fetchWorkspaces: async () => {
    set({ workspacesLoading: true });
    try {
      const response = await workspaceService.listWorkspaces();
      set({ workspaces: response.data, workspacesLoading: false });
    } catch (error) {
      console.error('Failed to fetch workspaces:', error);
      set({ workspacesLoading: false });
    }
  },

  /**
   * Load workspace by ID
   */
  loadWorkspace: async (workspaceId) => {
    set({ workspaceLoading: true, workspaceError: null });
    try {
      const response = await workspaceService.getWorkspace(workspaceId);
      const workspace = response.data;

      // Initialize local states for tabs
      const tabLocalStates = {};
      workspace.tabs.forEach((tab) => {
        tabLocalStates[tab.id] = {
          viewport: tab.viewport || { x: 0, y: 0, zoom: 1 },
          draggedPositions: {},
          hasUnsavedChanges: tab.has_unsaved_changes || false,
        };
      });

      set({
        workspace,
        tabLocalStates,
        workspaceLoading: false,
      });

      // Load tree data for active tab
      const activeTab = workspace.tabs.find((t) => t.is_active);
      if (activeTab) {
        get().loadActiveTabTreeData(activeTab.domain);
      }
    } catch (error) {
      console.error('Failed to load workspace:', error);
      set({
        workspaceError: error.response?.data?.message || error.message,
        workspaceLoading: false,
      });
    }
  },

  /**
   * Load or create default workspace
   */
  loadDefaultWorkspace: async () => {
    set({ workspaceLoading: true, workspaceError: null });
    try {
      const response = await workspaceService.getDefaultWorkspace();
      const workspace = response.data;

      // Initialize local states for tabs
      const tabLocalStates = {};
      workspace.tabs.forEach((tab) => {
        tabLocalStates[tab.id] = {
          viewport: tab.viewport || { x: 0, y: 0, zoom: 1 },
          draggedPositions: {},
          hasUnsavedChanges: tab.has_unsaved_changes || false,
        };
      });

      set({
        workspace,
        tabLocalStates,
        workspaceLoading: false,
      });

      // Load tree data for active tab
      const activeTab = workspace.tabs.find((t) => t.is_active);
      if (activeTab) {
        get().loadActiveTabTreeData(activeTab.domain);
      }
    } catch (error) {
      console.error('Failed to load default workspace:', error);
      set({
        workspaceError: error.response?.data?.message || error.message,
        workspaceLoading: false,
      });
    }
  },

  /**
   * Create new workspace
   */
  createWorkspace: async (data) => {
    try {
      const response = await workspaceService.createWorkspace(data);
      const newWorkspace = response.data;

      set((state) => ({
        workspaces: [newWorkspace, ...state.workspaces],
      }));

      return newWorkspace;
    } catch (error) {
      console.error('Failed to create workspace:', error);
      throw error;
    }
  },

  /**
   * Delete workspace
   */
  deleteWorkspace: async (workspaceId) => {
    try {
      await workspaceService.deleteWorkspace(workspaceId);
      set((state) => ({
        workspaces: state.workspaces.filter((w) => w.id !== workspaceId),
        workspace: state.workspace?.id === workspaceId ? null : state.workspace,
      }));
    } catch (error) {
      console.error('Failed to delete workspace:', error);
      throw error;
    }
  },

  // ==========================================================================
  // Tab Actions
  // ==========================================================================

  /**
   * Add a new tab to current workspace
   */
  addTab: async (domainId, name = '') => {
    const { workspace } = get();
    if (!workspace) return;

    try {
      const response = await workspaceService.addTab(workspace.id, {
        domain_id: domainId,
        name,
        is_active: true,
      });
      const newTab = response.data;

      // Initialize local state for new tab
      set((state) => ({
        workspace: {
          ...state.workspace,
          tabs: [...state.workspace.tabs, newTab],
        },
        tabLocalStates: {
          ...state.tabLocalStates,
          [newTab.id]: {
            viewport: { x: 0, y: 0, zoom: 1 },
            draggedPositions: {},
            hasUnsavedChanges: false,
          },
        },
      }));

      // Load tree data for new tab
      get().loadActiveTabTreeData(domainId);

      return newTab;
    } catch (error) {
      console.error('Failed to add tab:', error);
      throw error;
    }
  },

  /**
   * Remove a tab from current workspace
   */
  removeTab: async (tabId) => {
    const { workspace } = get();
    if (!workspace) return;

    try {
      await workspaceService.removeTab(workspace.id, tabId);

      set((state) => {
        const newTabs = state.workspace.tabs.filter((t) => t.id !== tabId);
        const { [tabId]: removed, ...newLocalStates } = state.tabLocalStates;

        return {
          workspace: {
            ...state.workspace,
            tabs: newTabs,
          },
          tabLocalStates: newLocalStates,
        };
      });

      // Load tree data for new active tab
      const { workspace: updatedWorkspace } = get();
      const newActiveTab = updatedWorkspace.tabs.find((t) => t.is_active);
      if (newActiveTab) {
        get().loadActiveTabTreeData(newActiveTab.domain);
      } else {
        set({ activeTabTreeData: null });
      }
    } catch (error) {
      console.error('Failed to remove tab:', error);
      throw error;
    }
  },

  /**
   * Activate a tab
   */
  activateTab: async (tabId) => {
    const { workspace, tabLocalStates } = get();
    if (!workspace) return;

    // Save current tab's viewport before switching
    const currentActiveTab = workspace.tabs.find((t) => t.is_active);
    if (currentActiveTab && tabLocalStates[currentActiveTab.id]?.viewport) {
      // Fire and forget - don't wait for response
      workspaceService.saveTabViewport(
        workspace.id,
        currentActiveTab.id,
        tabLocalStates[currentActiveTab.id].viewport
      ).catch(() => {});
    }

    try {
      const response = await workspaceService.activateTab(workspace.id, tabId);
      const activatedTab = response.data;

      // Update local state
      set((state) => ({
        workspace: {
          ...state.workspace,
          tabs: state.workspace.tabs.map((t) => ({
            ...t,
            is_active: t.id === tabId,
          })),
        },
      }));

      // Load tree data for activated tab
      get().loadActiveTabTreeData(activatedTab.domain);
    } catch (error) {
      console.error('Failed to activate tab:', error);
      throw error;
    }
  },

  /**
   * Reorder tabs
   */
  reorderTabs: async (tabIds) => {
    const { workspace } = get();
    if (!workspace) return;

    try {
      await workspaceService.reorderTabs(workspace.id, tabIds);

      // Update local order
      set((state) => {
        const tabsById = {};
        state.workspace.tabs.forEach((t) => {
          tabsById[t.id] = t;
        });

        const reorderedTabs = tabIds.map((id, index) => ({
          ...tabsById[id],
          order: index,
        }));

        return {
          workspace: {
            ...state.workspace,
            tabs: reorderedTabs,
          },
        };
      });
    } catch (error) {
      console.error('Failed to reorder tabs:', error);
      throw error;
    }
  },

  /**
   * Update tab name
   */
  updateTabName: async (tabId, name) => {
    const { workspace } = get();
    if (!workspace) return;

    try {
      await workspaceService.updateTab(workspace.id, tabId, { name });

      set((state) => ({
        workspace: {
          ...state.workspace,
          tabs: state.workspace.tabs.map((t) =>
            t.id === tabId ? { ...t, name } : t
          ),
        },
      }));
    } catch (error) {
      console.error('Failed to update tab name:', error);
      throw error;
    }
  },

  // ==========================================================================
  // Tree Data Actions
  // ==========================================================================

  /**
   * Load tree data for active tab
   */
  loadActiveTabTreeData: async (domainId) => {
    set({ treeDataLoading: true });
    try {
      const response = await domainService.getTree(domainId);
      set({ activeTabTreeData: response.data, treeDataLoading: false });
    } catch (error) {
      console.error('Failed to load tree data:', error);
      set({ activeTabTreeData: null, treeDataLoading: false });
    }
  },

  /**
   * Refresh active tab's tree data
   */
  refreshActiveTabTreeData: async () => {
    const { workspace } = get();
    if (!workspace) return;

    const activeTab = workspace.tabs.find((t) => t.is_active);
    if (activeTab) {
      await get().loadActiveTabTreeData(activeTab.domain);
    }
  },

  // ==========================================================================
  // Local State Management
  // ==========================================================================

  /**
   * Update tab's local viewport state
   */
  setTabViewport: (tabId, viewport) => {
    set((state) => ({
      tabLocalStates: {
        ...state.tabLocalStates,
        [tabId]: {
          ...state.tabLocalStates[tabId],
          viewport,
        },
      },
    }));
  },

  /**
   * Update tab's dragged positions
   */
  setTabDraggedPositions: (tabId, positions) => {
    set((state) => ({
      tabLocalStates: {
        ...state.tabLocalStates,
        [tabId]: {
          ...state.tabLocalStates[tabId],
          draggedPositions: positions,
          hasUnsavedChanges: Object.keys(positions).length > 0,
        },
      },
    }));
  },

  /**
   * Save tab's custom positions to server
   */
  saveTabPositions: async (tabId) => {
    const { workspace, tabLocalStates } = get();
    if (!workspace) return;

    const localState = tabLocalStates[tabId];
    if (!localState?.draggedPositions) return;

    try {
      await workspaceService.saveTabPositions(
        workspace.id,
        tabId,
        localState.draggedPositions
      );

      set((state) => ({
        tabLocalStates: {
          ...state.tabLocalStates,
          [tabId]: {
            ...state.tabLocalStates[tabId],
            hasUnsavedChanges: false,
          },
        },
      }));
    } catch (error) {
      console.error('Failed to save tab positions:', error);
      throw error;
    }
  },

  // ==========================================================================
  // Getters
  // ==========================================================================

  /**
   * Get active tab
   */
  getActiveTab: () => {
    const { workspace } = get();
    return workspace?.tabs.find((t) => t.is_active) || null;
  },

  /**
   * Get active tab's local state
   */
  getActiveTabLocalState: () => {
    const { workspace, tabLocalStates } = get();
    const activeTab = workspace?.tabs.find((t) => t.is_active);
    return activeTab ? tabLocalStates[activeTab.id] : null;
  },

  /**
   * Check if any tab has unsaved changes
   */
  hasAnyUnsavedChanges: () => {
    const { tabLocalStates } = get();
    return Object.values(tabLocalStates).some((state) => state.hasUnsavedChanges);
  },

  // ==========================================================================
  // Reset
  // ==========================================================================

  reset: () =>
    set({
      workspace: null,
      workspaceLoading: false,
      workspaceError: null,
      workspaces: [],
      workspacesLoading: false,
      activeTabTreeData: null,
      treeDataLoading: false,
      tabLocalStates: {},
    }),
}));

export default useWorkspaceStore;
