/**
 * Domain State Management with Zustand
 */
import { create } from 'zustand';
import { domainService, pageService } from '../services/domainService';

const useDomainStore = create((set, get) => ({
  // State
  domains: [],
  currentDomain: null,
  treeData: null,
  selectedPage: null,
  loading: false,
  error: null,

  // Actions
  fetchDomains: async () => {
    set({ loading: true, error: null });
    try {
      const response = await domainService.listDomains();
      // DRF pagination: results is the array
      set({ domains: response.data.results || [], loading: false });
    } catch (error) {
      set({
        error: error.response?.data?.message || error.message || 'Failed to fetch domains',
        loading: false
      });
    }
  },

  createDomain: async (domainData) => {
    set({ loading: true, error: null });
    try {
      const response = await domainService.createDomain(domainData);
      const { domains } = get();
      set({
        domains: [...domains, response.data],
        currentDomain: response.data,
        loading: false
      });
      return response.data;
    } catch (error) {
      set({
        error: error.response?.data?.message || error.message || 'Failed to create domain',
        loading: false
      });
      throw error;
    }
  },

  setCurrentDomain: async (domainId) => {
    set({ loading: true, error: null, treeData: null }); // Clear previous tree data
    try {
      const response = await domainService.getDomain(domainId);
      set({
        currentDomain: response.data,
        loading: false
      });
    } catch (error) {
      set({
        error: error.response?.data?.message || error.message || 'Failed to fetch domain',
        loading: false
      });
    }
  },

  refreshDomain: async (domainId) => {
    set({ loading: true, error: null });
    try {
      await domainService.refreshDomain(domainId);
      // Fetch updated domain and tree data
      const [domainResponse, treeResponse] = await Promise.all([
        domainService.getDomain(domainId),
        domainService.getTree(domainId)
      ]);
      set({
        currentDomain: domainResponse.data,
        treeData: treeResponse.data,
        loading: false
      });
    } catch (error) {
      set({
        error: error.response?.data?.message || error.message || 'Failed to refresh domain',
        loading: false
      });
    }
  },

  refreshSearchConsole: async (domainId) => {
    set({ loading: true, error: null });
    try {
      await domainService.refreshSearchConsole(domainId);
      // Fetch updated domain and tree data
      const [domainResponse, treeResponse] = await Promise.all([
        domainService.getDomain(domainId),
        domainService.getTree(domainId)
      ]);
      set({
        currentDomain: domainResponse.data,
        treeData: treeResponse.data,
        loading: false
      });
    } catch (error) {
      set({
        error: error.response?.data?.message || error.message || 'Failed to refresh Search Console data',
        loading: false
      });
    }
  },

  scanDomain: async (domainId) => {
    set({ loading: true, error: null });
    try {
      const response = await domainService.scanDomain(domainId);
      set({ loading: false });
      return response.data; // Returns task_id for background job
    } catch (error) {
      set({
        error: error.response?.data?.message || error.message || 'Failed to start scan',
        loading: false
      });
      throw error;
    }
  },

  fetchTree: async (domainId) => {
    set({ loading: true, error: null });
    try {
      const response = await domainService.getTree(domainId);
      set({
        treeData: response.data,
        loading: false
      });
    } catch (error) {
      set({
        error: error.response?.data?.message || error.message || 'Failed to fetch tree',
        loading: false
      });
    }
  },

  // Optimized: Fetch domain and tree in parallel
  fetchDomainWithTree: async (domainId, clearTreeData = false) => {
    // Only clear treeData on initial load, not on refresh (to preserve viewport)
    if (clearTreeData) {
      set({ loading: true, error: null, treeData: null });
    } else {
      set({ loading: true, error: null });
    }
    try {
      // Fetch both in parallel
      const [domainResponse, treeResponse] = await Promise.all([
        domainService.getDomain(domainId),
        domainService.getTree(domainId)
      ]);
      set({
        currentDomain: domainResponse.data,
        treeData: treeResponse.data,
        loading: false
      });
    } catch (error) {
      set({
        error: error.response?.data?.message || error.message || 'Failed to fetch domain data',
        loading: false
      });
    }
  },

  setSelectedPage: async (pageId) => {
    if (!pageId) {
      set({ selectedPage: null });
      return;
    }

    set({ loading: true, error: null });
    try {
      const [pageResponse, metricsResponse] = await Promise.all([
        pageService.getPage(pageId),
        pageService.getPageMetrics(pageId)
      ]);
      set({
        selectedPage: {
          ...pageResponse.data,
          metrics: metricsResponse.data
        },
        loading: false
      });
    } catch (error) {
      set({
        error: error.response?.data?.message || error.message || 'Failed to fetch page details',
        loading: false
      });
    }
  },

  deleteDomain: async (domainId) => {
    set({ loading: true, error: null });
    try {
      await domainService.deleteDomain(domainId);
      const { domains } = get();
      set({
        domains: domains.filter(d => d.id !== domainId),
        currentDomain: null,
        treeData: null,
        loading: false
      });
    } catch (error) {
      set({
        error: error.response?.data?.message || error.message || 'Failed to delete domain',
        loading: false
      });
      throw error;
    }
  },

  clearError: () => set({ error: null }),
}));

export default useDomainStore;
