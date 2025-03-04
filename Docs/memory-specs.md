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

### 8. Bot Memory Usage

1. **Message Processing Flow**
   ```
   User Message → Memory Check → Response Generation → Memory Update
        ↓              ↓               ↓                   ↓
   Validate Input   Get Context    Use Context      Store New Messages
   ```

2. **Context Assembly**
   - **Short-term Priority**
     ```python
     context = {
       "recent": short_term[-10:],  # Last 10 messages
       "history_summary": history_context,
       "relevant_mid_term": mid_term.filter(relevance_score > 0.7)
     }
     ```
   - **Context Selection**
     - Recent messages always included
     - History context if available
     - Relevant mid-term messages based on topic

3. **Memory Reading Sequence**
   ```
   1. Check history_context.json
      ↓
   2. Load short_term.json (last 50 messages)
      ↓
   3. If needed, check mid_term.json
      ↓
   4. On demand: access whole_history.json
   ```

4. **Context Utilization**
   - **Command Processing**
     - `/historycontext`: Reads and displays history_context.json
     - `/analyze`: Triggers whole history analysis
     - `/clear`: Resets short-term memory
     - `/context`: Shows current conversation context

   - **Conversation Flow**
     ```
     1. Load recent context (last 10 messages)
     2. Add history summary if relevant
     3. Include specific mid-term memories if topic matches
     4. Generate response using combined context
     ```

5. **Memory Access Patterns**
   - **High Frequency**
     - Short-term memory: Every message
     - History context: Every few messages
   - **Medium Frequency**
     - Mid-term memory: Topic changes
     - Context regeneration: 50 message threshold
   - **Low Frequency**
     - Whole history: Analysis commands
     - Storage cleanup: Daily

6. **Context Switching**
   ```
   New Topic → Check Mid-term → Update Context → Adjust Response
       ↓            ↓               ↓               ↓
   Detect Change  Find Related   Merge Context   Apply Rules
   ```

7. **Memory-Based Features**
   - **Conversation Continuity**
     - Track ongoing discussions
     - Maintain context across messages
     - Handle topic transitions
   
   - **User Preferences**
     - Remember interaction styles
     - Store user-specific contexts
     - Adapt responses based on history

   - **Learning Patterns**
     - Identify common topics
     - Track successful interactions
     - Adapt to user communication style

8. **Memory Optimization**
   - **Context Relevance**
     ```json
     {
       "priority": 1-5,
       "relevance_score": 0.0-1.0,
       "topic_tags": ["tag1", "tag2"],
       "expiration": "timestamp"
     }
     ```
   
   - **Smart Loading**
     - Load only relevant context
     - Prioritize recent interactions
     - Cache frequently accessed data

   - **Memory Cleanup**
     - Archive old conversations
     - Remove redundant context
     - Compress historical data

9. **Error Recovery**
   - **Missing Context**
     ```
     No Context → Use Defaults → Rebuild Context → Normal Operation
         ↓            ↓              ↓                ↓
     Log Error    Basic Mode    Background Task    Resume
     ```
   
   - **Corrupted Memory**
     - Fall back to available components
     - Rebuild from whole history
     - Log and report issues

10. **Performance Considerations**
    - Cache recent context in memory
    - Lazy load historical data
    - Batch memory updates
    - Asynchronous context analysis
