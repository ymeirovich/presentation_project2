# Prompt System Test Plan

## Overview
This test plan covers the current prompt functionality in the PresGen-Assess system, ensuring comprehensive coverage before implementing the prompt individuation changes.

## Current System Architecture

### Prompt Storage Locations
1. **Database Columns**: `certification_profiles.assessment_prompt`, `presentation_prompt`, `gap_analysis_prompt`
2. **JSON Template**: `certification_profiles.assessment_template._chromadb_prompts`
3. **Default Prompts**: `src/service/default_prompts.py`

### Data Flow
```
UI Form → Proxy Layer → Backend API → Database → Backend API → Proxy Layer → UI Display
```

## Test Categories

### 1. Database Layer Tests (`test_prompt_database.py`)

#### 1.1 Direct Database Operations
- **Create**: Insert certification profile with prompt values
- **Read**: Retrieve prompt values from database columns
- **Update**: Modify existing prompt values
- **Delete**: Remove certification profile with prompts

#### 1.2 Schema Validation
- **Nullable Fields**: Verify prompts can be NULL
- **Text Length**: Test large prompt text storage
- **Data Types**: Confirm TEXT column behavior

#### 1.3 Migration Safety
- **Existing Data**: Verify current data structure integrity
- **Backward Compatibility**: Ensure existing queries work

### 2. API Endpoint Tests (`test_prompt_api.py`)

#### 2.1 Certification Profile CRUD
```python
class TestCertificationPromptAPI:
    async def test_create_profile_with_prompts(self):
        """Test creating certification profile with prompt data."""

    async def test_get_profile_returns_prompts(self):
        """Test retrieving profile includes prompt fields."""

    async def test_update_profile_prompts(self):
        """Test updating only prompt fields."""

    async def test_list_profiles_includes_prompts(self):
        """Test list endpoint includes prompt data."""
```

#### 2.2 Response Schema Validation
- **Field Presence**: All endpoints return prompt fields
- **Data Type**: Prompts are strings or null
- **Consistency**: Same prompt data across different endpoints

#### 2.3 Error Handling
- **Invalid Prompt Data**: Handle malformed prompt text
- **Missing Profiles**: 404 responses for non-existent profiles
- **Schema Violations**: Validation error responses

### 3. Proxy Layer Tests (`test_prompt_proxy.py`)

#### 3.1 Data Transformation
```python
class TestProxyPromptHandling:
    def test_put_request_includes_prompts(self):
        """Test proxy forwards prompt fields in PUT requests."""

    def test_get_response_transforms_prompts(self):
        """Test proxy correctly transforms prompt response data."""

    def test_prompt_field_filtering(self):
        """Test proxy handles empty/null prompt fields correctly."""
```

#### 3.2 Request/Response Logging
- **Correlation IDs**: Track requests through proxy
- **Data Transformation**: Log before/after prompt data
- **Error Propagation**: Proxy error handling

### 4. Frontend Form Tests (`test_prompt_ui.py`)

#### 4.1 Form Validation
```javascript
describe('Prompt Form Handling', () => {
  test('form includes prompt fields', () => {
    // Test prompt fields are present in form
  });

  test('form submits prompt data', () => {
    // Test prompt values are included in submission
  });

  test('form loads existing prompts', () => {
    // Test form populates with existing prompt values
  });
});
```

#### 4.2 User Interactions
- **Data Entry**: User can enter custom prompt text
- **Save/Load**: Prompt data persists through save/reload cycle
- **Validation**: Form validates prompt field requirements

### 5. Integration Tests (`test_prompt_integration.py`)

#### 5.1 End-to-End Workflow
```python
class TestPromptEndToEnd:
    async def test_full_prompt_lifecycle(self):
        """Test complete prompt data flow from UI to database and back."""
        # 1. Create certification profile with prompts via API
        # 2. Retrieve via different endpoints
        # 3. Update prompts
        # 4. Verify changes persist
        # 5. Test UI form load/save cycle

    async def test_prompt_data_integrity(self):
        """Test prompt data maintains integrity through all transformations."""
        # Test with various prompt text scenarios:
        # - Long text
        # - Special characters
        # - Empty/null values
        # - Unicode content
```

#### 5.2 Cross-System Consistency
- **API vs Database**: Verify API responses match database state
- **Multiple Endpoints**: Same prompt data across all endpoints
- **Form vs API**: UI form data matches API responses

### 6. Performance Tests (`test_prompt_performance.py`)

#### 6.1 Load Testing
- **Large Prompt Text**: Performance with extensive prompt content
- **Multiple Profiles**: Bulk operations with prompt data
- **Concurrent Access**: Multiple users editing prompts

#### 6.2 Caching Behavior
- **Response Caching**: Verify prompt data caching works correctly
- **Cache Invalidation**: Updates invalidate cached prompt data

### 7. Security Tests (`test_prompt_security.py`)

#### 7.1 Input Validation
- **XSS Prevention**: HTML/script injection in prompts
- **SQL Injection**: Database query safety
- **Input Sanitization**: Prompt text sanitization

#### 7.2 Access Control
- **Authorization**: Only authorized users can modify prompts
- **Data Isolation**: Users can't access other users' prompts

## Test Data Scenarios

### Prompt Content Variations
```python
PROMPT_TEST_CASES = [
    {
        "name": "normal_text",
        "assessment_prompt": "Generate assessment questions for certification.",
        "presentation_prompt": "Create presentation slides for learning.",
        "gap_analysis_prompt": "Analyze learning gaps and provide recommendations."
    },
    {
        "name": "long_text",
        "assessment_prompt": "A" * 10000,  # Test large text handling
        "presentation_prompt": "B" * 5000,
        "gap_analysis_prompt": "C" * 8000
    },
    {
        "name": "special_characters",
        "assessment_prompt": "Test with 'quotes', \"double quotes\", and {braces}",
        "presentation_prompt": "Unicode: 你好 🌟 café naïve résumé",
        "gap_analysis_prompt": "JSON: {\"key\": \"value\", \"array\": [1, 2, 3]}"
    },
    {
        "name": "empty_values",
        "assessment_prompt": None,
        "presentation_prompt": "",
        "gap_analysis_prompt": "   "  # Whitespace only
    },
    {
        "name": "multiline_text",
        "assessment_prompt": """
        Line 1 of prompt
        Line 2 with formatting

        Line 4 after blank line
        """,
        "presentation_prompt": "Single line prompt",
        "gap_analysis_prompt": "Another\nmultiline\nprompt"
    }
]
```

### Certification Profile Variations
- **New Profile**: Clean slate with custom prompts
- **Existing Profile**: Profile with existing default prompts
- **Legacy Profile**: Profile created before prompt system
- **Migrated Profile**: Profile with dual-storage data

## Test Execution Strategy

### Phase 1: Baseline Testing (Before Changes)
1. **Run existing tests**: `python3 -m pytest tests/ -v`
2. **Create new prompt tests**: Implement comprehensive prompt test suite
3. **Establish coverage baseline**: Generate coverage report
4. **Document current behavior**: Capture expected behavior patterns

### Phase 2: Development Testing (During Changes)
1. **Test-driven development**: Write tests before implementing changes
2. **Incremental validation**: Run tests after each change
3. **Regression testing**: Ensure existing functionality remains intact
4. **Integration validation**: Test cross-system interactions

### Phase 3: Validation Testing (After Changes)
1. **Full test suite**: Run all tests with new implementation
2. **Performance comparison**: Compare before/after performance
3. **User acceptance**: Validate from user perspective
4. **Production readiness**: Final validation before deployment

## Continuous Integration Integration

### Pre-commit Hooks
```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running prompt system tests..."
python3 -m pytest tests/test_prompt_*.py -v

if [ $? -ne 0 ]; then
    echo "Prompt tests failed. Commit aborted."
    exit 1
fi

echo "Running full test suite..."
python3 -m pytest tests/ -v

if [ $? -ne 0 ]; then
    echo "Test suite failed. Commit aborted."
    exit 1
fi
```

### GitHub Actions Workflow
```yaml
name: Prompt System Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: pip3 install -r requirements.txt
      - name: Run prompt system tests
        run: python3 -m pytest tests/test_prompt_*.py -v --cov=src
      - name: Run full test suite
        run: python3 -m pytest tests/ -v --cov=src
```

## Success Criteria

### Test Coverage Goals
- **Database Layer**: 100% coverage of prompt-related operations
- **API Endpoints**: 100% coverage of prompt field handling
- **Integration**: 95% coverage of end-to-end workflows
- **Overall**: 90% overall code coverage for prompt system

### Quality Gates
- ✅ All tests pass consistently
- ✅ No regression in existing functionality
- ✅ Performance within acceptable limits
- ✅ Security validation passes
- ✅ User experience validation successful

## Risk Mitigation

### Test Environment Safety
- **Isolated Database**: Use test database for all testing
- **Mock External Services**: Mock external API calls
- **Data Cleanup**: Ensure tests clean up after themselves

### Rollback Planning
- **Snapshot Before Changes**: Database and code snapshots
- **Test Rollback Procedures**: Validate rollback scenarios
- **Emergency Procedures**: Quick rollback if issues detected

This comprehensive test plan ensures that all current prompt functionality is thoroughly validated before implementing the prompt individuation changes, providing a safety net against regressions and ensuring system stability throughout the development process.