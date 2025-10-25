// MESSAGE TYPES - Use these constants everywhere
export const MESSAGE_TYPES = {
    GET_POLICY_TEXT: 'GET_POLICY_TEXT',
    ANALYZE_REQUEST: 'analyze_request',
    ANALYSIS_RESULT: 'analysis_result',
    ERROR: 'error'
  };
  
  // Expected analysis response from backend
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
          { text: 'We collect your name, email, and browsing activity.', keywords: ['collect', 'email'] }
        ]
      },
      {
        name: 'Third-Party Sharing/Selling',
        score: 25,
        weight: 0.20,
        reasons: ['May sell data to third parties', 'No clear opt-out mechanism'],
        evidence: [
          { text: 'We may share your information with partners for marketing.', keywords: ['share', 'partners'] }
        ]
      },
      {
        name: 'Purpose Limitation',
        score: 55,
        weight: 0.10,
        reasons: ['States general purposes', 'Includes vague "compatible purposes" clause'],
        evidence: []
      },
      {
        name: 'User Control & Rights',
        score: 70,
        weight: 0.15,
        reasons: ['Provides access and deletion rights', 'Includes "Do Not Sell" link'],
        evidence: []
      },
      {
        name: 'Retention & Deletion',
        score: 35,
        weight: 0.10,
        reasons: ['No specific retention period', 'Retains data "as long as necessary"'],
        evidence: []
      },
      {
        name: 'Security Practices',
        score: 75,
        weight: 0.10,
        reasons: ['Mentions encryption', 'References industry standards'],
        evidence: []
      },
      {
        name: 'International Transfers & Jurisdiction',
        score: 50,
        weight: 0.10,
        reasons: ['Mentions international transfers', 'No specific safeguards mentioned'],
        evidence: []
      },
      {
        name: 'Children/Minors & Sensitive Data',
        score: 80,
        weight: 0.10,
        reasons: ['COPPA compliant', 'Restricts biometric data collection'],
        evidence: []
      }
    ],
    timestamp: Date.now(),
    analyzedTextLength: 2847,
    isWholePage: false
  };