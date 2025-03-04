# Memory Management Specification

## Core Components

### 1. Memory Types
- **Short-term Memory**
  - Capacity: 50 messages
  - Purpose: Immediate conversation context
  - Update: Real-time with each message
  - Location: `memory/account_{id}/short_term.json`

- **Mid-term Memory**
  - Capacity: 200 messages
  - Purpose: Extended conversation context
  - Update: When short-term overflows
  - Location: `memory/account_{id}/mid_term.json`

- **Whole History**
  - Capacity: Unlimited
  - Purpose: Complete conversation archive
  - Update: Every message
  - Location: `memory/account_{id}/whole_history.json`

- **History Context**
  - Capacity: Dynamic
  - Purpose: Analyzed conversation summaries
  - Update: On trigger conditions
  - Location: `memory/account_{id}/history_context.json`

### 2. Initialization Process

1. **Account Creation**
   ```json
   {
     "account_id": "<id>",
     "created_at": "<timestamp>",
     "memory_status": {
       "short_term": "initialized",
       "mid_term": "initialized",
       "whole_history": "initialized",
       "history_context": "initialized"
     }
   }
   ```

2. **Memory Files Creation**
   - Create directory structure
   - Initialize empty memory files
   - Set initial status flags

3. **Initial Context**
   - Create baseline history context
   - Record initialization timestamp
   - Set memory component states

### 3. Update Lifecycle

1. **Message Reception**
   ```
   New Message → Short-term → Whole History
                     ↓
              Check Threshold
                     ↓
              Mid-term (if needed)
                     ↓
              Context Update (if triggered)
   ```

2. **Short-term Updates**
   - Add new message
   - Update timestamp
   - Check 50-message threshold
   - Trigger mid-term update if needed

3. **Mid-term Updates**
   - Triggered by short-term overflow
   - Maintain 200 message window
   - Update status and timestamps

4. **Whole History Updates**
   - Append every message
   - Maintain chronological order
   - Update metadata

5. **Context Generation**
   Triggers:
   - Short-term reaches 50 messages
   - Manual regeneration request
   - Periodic analysis (24h)
   - Significant topic change

### 4. Status Management

Each memory component maintains a status:
```json
{
  "status": "active|failing|initializing",
  "last_update": "<timestamp>",
  "message_count": "<number>",
  "health_check": "<timestamp>"
}
```

### 5. Error Handling

1. **Database Failures**
   - Switch to file fallback
   - Mark status as "failing"
   - Attempt recovery on next operation

2. **Corruption Recovery**
   - Detect invalid states
   - Attempt automatic repair
   - Fall back to initialization if needed

3. **Synchronization**
   - Handle concurrent updates
   - Maintain consistency across components
   - Log state changes

### 6. Performance Optimization

1. **Message Deduplication**
   - Track message hashes
   - Remove duplicates on insert
   - Maintain temporal order

2. **Context Summarization**
   - Intelligent chunking
   - Priority-based analysis
   - Relevant information extraction

3. **Storage Management**
   - Periodic cleanup
   - Archive old messages
   - Optimize storage format

### 7. Health Monitoring

1. **Component Health**
   ```json
   {
     "component": "<memory_type>",
     "status": "<status_code>",
     "last_check": "<timestamp>",
     "issues": ["<issue_description>"]
   }
   ```

2. **Performance Metrics**
   - Response times
   - Storage usage
   - Update frequency
   - Error rates

3. **Alerting Thresholds**
   - Component failures
   - Capacity warnings
   - Performance degradation
   - Synchronization issues
