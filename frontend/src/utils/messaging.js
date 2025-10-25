// src/utils/messaging.js

// MESSAGE TYPES - constants for all messages
export const MESSAGE_TYPES = {
  GET_POLICY_TEXT: 'GET_POLICY_TEXT',
  ANALYZE_TEXT: 'ANALYZE_TEXT',
  GET_CACHED: 'GET_CACHED',
  CLEAR_CACHE: 'CLEAR_CACHE'
};

// Mock data for development (looks like real backend response)
export const MOCK_ANALYSIS = {
  trustScore: 42,
  riskLevel: 'medium',
  categories: [
    {
      name: 'Data Collection',
      score: 60,
      weight: 0.15,
      reasons: ['Clearly states what data is collected', 'Does not specify limits on sensitive data'],
      evidence: [
        { 
          text: 'We collect your name, email, and browsing activity on our site.',
          keywords: ['collect', 'email', 'browsing activity'],
          highlighted: 'We <mark>collect</mark> your name, <mark>email</mark>, and <mark>browsing activity</mark> on our site.'
        }
      ]
    },
    {
      name: 'Third-Party Sharing/Selling',
      score: 25,
      weight: 0.20,
      reasons: ['May sell data to third parties', 'No clear opt-out mechanism'],
      evidence: [
        {
          text: 'We may share your information with our partners for marketing purposes.',
          keywords: ['share', 'partners', 'marketing'],
          highlighted: 'We may <mark>share</mark> your information with our <mark>partners</mark> for <mark>marketing</mark> purposes.'
        }
      ]
    },
    {
      name: 'Purpose Limitation',
      score: 55,
      weight: 0.10,
      reasons: ['States general purposes', 'Vague language about compatible uses'],
      evidence: []
    },
    {
      name: 'User Control & Rights',
      score: 70,
      weight: 0.15,
      reasons: ['Provides access and deletion rights', 'CCPA compliant'],
      evidence: []
    },
    {
      name: 'Retention & Deletion',
      score: 35,
      weight: 0.10,
      reasons: ['No specific retention period', 'Retains data indefinitely'],
      evidence: []
    },
    {
      name: 'Security Practices',
      score: 75,
      weight: 0.10,
      reasons: ['Mentions encryption', 'Industry-standard security'],
      evidence: []
    },
    {
      name: 'International Transfers & Jurisdiction',
      score: 50,
      weight: 0.10,
      reasons: ['Mentions international transfers', 'No specific safeguards'],
      evidence: []
    },
    {
      name: 'Children/Minors + Sensitive Data',
      score: 80,
      weight: 0.10,
      reasons: ['COPPA compliant', 'Protects minors'],
      evidence: []
    }
  ],
  timestamp: Date.now(),
  analyzedTextLength: 2847
};