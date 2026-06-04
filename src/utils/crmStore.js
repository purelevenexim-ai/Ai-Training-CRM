/**
 * CRM State Management - Zustand Store
 * Centralized state for journeys, customers, analytics, and WebSocket
 * Phase 3+ Integration: WebSocket, real-time metrics, step logs
 */

import { create } from 'zustand';
import crmApi from './crmApi';

export const useCrmStore = create((set, get) => ({
  // ═══════════════════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════════════════

  // Journeys
  journeys: [],
  journeyAnalytics: null,
  selectedJourney: null,
  loadingJourneys: false,

  // Customer Timeline
  customerTimeline: null,
  selectedCustomerEmail: null,
  loadingTimeline: false,

  // Journey Builder (Phase 3)
  builderNodes: [],
  builderEdges: [],
  builderJourneyName: '',
  builderJourneyTrigger: 'customer_create',

  // WebSocket State (Phase 3)
  wsConnected: false,
  metricsData: null,
  stepLogs: [],
  wsError: null,

  // UI State
  view: 'analytics', // analytics | timeline | builder
  error: null,
  success: null,

  // ═══════════════════════════════════════════════════════════════════════
  // JOURNEY ACTIONS
  // ═══════════════════════════════════════════════════════════════════════

  fetchJourneys: async () => {
    set({ loadingJourneys: true });
    try {
      const journeys = await crmApi.listJourneys();
      set({ journeys, error: null });
    } catch (err) {
      set({ error: err.message });
    }
    set({ loadingJourneys: false });
  },

  fetchJourneyAnalytics: async () => {
    try {
      const journeyAnalytics = await crmApi.getJourneyAnalytics();
      set({ journeyAnalytics, error: null });
    } catch (err) {
      set({ error: err.message });
    }
  },

  /**
   * Merge real-time metrics from WebSocket with journey analytics
   * This is called when metricsData is updated by the socket
   */
  integrateRealtimeMetrics: () => {
    set((state) => {
      const currentAnalytics = state.journeyAnalytics || {
        total_active_instances: 0,
        total_completed: 0,
        journeys: [],
      };

      // If we have real-time metrics, merge them
      if (state.metricsData) {
        return {
          journeyAnalytics: {
            ...currentAnalytics,
            // Update with real-time data
            total_active_instances: state.metricsData.active_instances ?? currentAnalytics.total_active_instances,
            steps_today: state.metricsData.steps_today,
            emails_sent: state.metricsData.emails_sent,
            conversions: state.metricsData.conversions,
            // Merge into existing journeys
            journeys: (currentAnalytics.journeys || []).map((j) => ({
              ...j,
              // Real-time updates for this journey
              ...(state.metricsData.journey_id === j.id && {
                active_instances: state.metricsData.active_instances,
                email_sent: state.metricsData.emails_sent,
                whatsapp_sent: state.metricsData.whatsapp_sent,
              }),
            })),
          },
        };
      }

      return state;
    });
  },

  createJourney: async (journeyData) => {
    try {
      const newJourney = await crmApi.createJourney(journeyData);
      set((state) => ({
        journeys: [...state.journeys, newJourney],
        success: 'Journey created successfully',
        error: null,
      }));
      return newJourney;
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  updateJourney: async (journeyId, data) => {
    try {
      const updated = await crmApi.updateJourney(journeyId, data);
      set((state) => ({
        journeys: state.journeys.map((j) => (j.id === journeyId ? updated : j)),
        success: 'Journey updated successfully',
        error: null,
      }));
      return updated;
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  selectJourney: (journey) => {
    set({ selectedJourney: journey });
  },

  // ═══════════════════════════════════════════════════════════════════════
  // CUSTOMER TIMELINE ACTIONS
  // ═══════════════════════════════════════════════════════════════════════

  fetchCustomerTimeline: async (email) => {
    set({ loadingTimeline: true, selectedCustomerEmail: email });
    try {
      const [intelligence, activity] = await Promise.all([
        crmApi.getCustomerTimeline(email),
        crmApi.get('/comm/timeline', { email }),
      ]);

      const messages = Array.isArray(activity?.events)
        ? activity.events
            .filter((event) => event.type === 'communication')
            .map((event) => ({
              channel: event.channel || 'email',
              template_id: event.source_id || event.template_name || event.event_type,
              sent_at: event.ts,
              status: (event.event_type || 'SENT').replace(/^EMAIL_/, '').replace(/^WA_/, '').toUpperCase(),
            }))
        : [];

      const nextActionLabel = intelligence?.next_action || intelligence?.ai?.next_action || '';
      const nextAction = nextActionLabel
        ? {
            step_type: String(nextActionLabel).includes('whatsapp') ? 'whatsapp' : 'email',
            step_name: nextActionLabel,
            scheduled_at: null,
            reason: intelligence?.ai?.reason || '',
          }
        : null;

      set({
        customerTimeline: {
          ...intelligence,
          active_journeys: intelligence?.active_journeys || intelligence?.journeys?.active || [],
          next_action: nextAction,
          messages,
          unified_timeline: activity?.events || [],
          unified_summary: activity?.summary || null,
        },
        error: null,
      });
    } catch (err) {
      set({ error: err.message });
    }
    set({ loadingTimeline: false });
  },

  enrollInJourney: async (customerId, journeyId) => {
    try {
      await crmApi.enrollCustomerInJourney(customerId, journeyId);
      set({ success: 'Customer enrolled in journey' });
      // Refresh timeline
      const email = get().selectedCustomerEmail;
      if (email) {
        get().fetchCustomerTimeline(email);
      }
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  pauseJourney: async (instanceId) => {
    try {
      await crmApi.updateJourneyInstance(instanceId, { status: 'PAUSED' });
      set({ success: 'Journey paused' });
      const email = get().selectedCustomerEmail;
      if (email) {
        get().fetchCustomerTimeline(email);
      }
    } catch (err) {
      set({ error: err.message });
    }
  },

  resumeJourney: async (instanceId) => {
    try {
      await crmApi.updateJourneyInstance(instanceId, { status: 'ACTIVE' });
      set({ success: 'Journey resumed' });
      const email = get().selectedCustomerEmail;
      if (email) {
        get().fetchCustomerTimeline(email);
      }
    } catch (err) {
      set({ error: err.message });
    }
  },

  // ═══════════════════════════════════════════════════════════════════════
  // JOURNEY BUILDER ACTIONS (Phase 3)
  // ═══════════════════════════════════════════════════════════════════════

  setBuilderJourneyName: (name) => {
    set({ builderJourneyName: name });
  },

  setBuilderJourneyTrigger: (trigger) => {
    set({ builderJourneyTrigger: trigger });
  },

  setBuilderNodes: (nodes) => {
    set({ builderNodes: nodes });
  },

  setBuilderEdges: (edges) => {
    set({ builderEdges: edges });
  },

  resetBuilder: () => {
    set({
      builderNodes: [],
      builderEdges: [],
      builderJourneyName: '',
      builderJourneyTrigger: 'customer_create',
    });
  },

  // ═══════════════════════════════════════════════════════════════════════
  // WEBSOCKET ACTIONS (Phase 3)
  // ═══════════════════════════════════════════════════════════════════════

  setWsConnected: (connected) => {
    set({ wsConnected: connected });
  },

  setWsError: (error) => {
    set({ wsError: error });
  },

  updateMetricsData: (metricsData) => {
    set({ metricsData, wsError: null });
    // Trigger integration of real-time metrics with analytics
    get().integrateRealtimeMetrics();
  },

  addStepLog: (stepLog) => {
    set((state) => ({
      stepLogs: [
        ...state.stepLogs,
        {
          ...stepLog,
          timestamp: new Date().toISOString(),
        },
      ].slice(-50), // Keep last 50 logs
    }));
  },

  clearStepLogs: () => {
    set({ stepLogs: [] });
  },

  // ═══════════════════════════════════════════════════════════════════════
  // UI ACTIONS
  // ═══════════════════════════════════════════════════════════════════════

  setView: (view) => set({ view }),

  clearError: () => set({ error: null }),

  clearSuccess: () => set({ success: null }),
}));

export default useCrmStore;
