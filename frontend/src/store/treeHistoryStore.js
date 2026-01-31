/**
 * Tree History Store
 * Manages undo/redo history with automatic sessionStorage persistence
 *
 * Features:
 * - Automatic sessionStorage sync (clears on tab close)
 * - Type-safe action recording
 * - Undo/redo operations
 * - Per-domain history isolation
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useTreeHistoryStore = create(
  persist(
    (set, get) => ({
      // History state by domain ID
      histories: {}, // { [domainId]: { items: [], index: -1 } }

      /**
       * Get history for a specific domain
       */
      getHistory: (domainId) => {
        const histories = get().histories;
        return histories[domainId] || { items: [], index: -1 };
      },

      /**
       * Add action to history
       */
      addToHistory: (domainId, action) => {
        set((state) => {
          const currentHistory = state.histories[domainId] || { items: [], index: -1 };

          // Remove future items after current index
          const newItems = currentHistory.items.slice(0, currentHistory.index + 1);
          newItems.push({
            ...action,
            timestamp: Date.now(),
          });

          return {
            histories: {
              ...state.histories,
              [domainId]: {
                items: newItems,
                index: newItems.length - 1,
              },
            },
          };
        });
      },

      /**
       * Undo last action
       */
      undo: (domainId) => {
        const history = get().getHistory(domainId);

        if (history.index < 0) {
          return null; // Nothing to undo
        }

        const action = history.items[history.index];

        // Decrement index
        set((state) => ({
          histories: {
            ...state.histories,
            [domainId]: {
              ...history,
              index: history.index - 1,
            },
          },
        }));

        return action;
      },

      /**
       * Redo next action
       */
      redo: (domainId) => {
        const history = get().getHistory(domainId);

        if (history.index >= history.items.length - 1) {
          return null; // Nothing to redo
        }

        const action = history.items[history.index + 1];

        // Increment index
        set((state) => ({
          histories: {
            ...state.histories,
            [domainId]: {
              ...history,
              index: history.index + 1,
            },
          },
        }));

        return action;
      },

      /**
       * Clear history for a domain
       */
      clearHistory: (domainId) => {
        set((state) => ({
          histories: {
            ...state.histories,
            [domainId]: { items: [], index: -1 },
          },
        }));
      },

      /**
       * Clear all histories
       */
      clearAllHistories: () => {
        set({ histories: {} });
      },

      /**
       * Get undo count for a domain
       */
      getUndoCount: (domainId) => {
        const history = get().getHistory(domainId);
        return history.index + 1;
      },

      /**
       * Get redo count for a domain
       */
      getRedoCount: (domainId) => {
        const history = get().getHistory(domainId);
        return history.items.length - history.index - 1;
      },

      /**
       * Check if undo is available
       */
      canUndo: (domainId) => {
        const history = get().getHistory(domainId);
        return history.index >= 0;
      },

      /**
       * Check if redo is available
       */
      canRedo: (domainId) => {
        const history = get().getHistory(domainId);
        return history.index < history.items.length - 1;
      },
    }),
    {
      name: 'tree-history', // sessionStorage key
      version: 1,

      // Use sessionStorage instead of localStorage (clears on tab close)
      storage: {
        getItem: (name) => {
          const str = sessionStorage.getItem(name);
          return str ? JSON.parse(str) : null;
        },
        setItem: (name, value) => {
          sessionStorage.setItem(name, JSON.stringify(value));
        },
        removeItem: (name) => {
          sessionStorage.removeItem(name);
        },
      },

      // Persist histories only
      partialize: (state) => ({
        histories: state.histories,
      }),
    }
  )
);

export default useTreeHistoryStore;
