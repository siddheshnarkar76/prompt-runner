# Test Suite Documentation

## 📋 Overview

Comprehensive test suite for the Streamlit Prompt Runner project using pytest.

## 🎯 Test Coverage

### Test Files

1. **`test_mcp.py`** - MCP (Model Context Protocol) Tests
   - Server connectivity
   - Rule operations (save/retrieve)
   - Feedback system
   - Geometry logging
   - Multi-city support

2. **`test_agents.py`** - Agent Functionality Tests
   - Calculator agent
   - RL (Reinforcement Learning) agent
   - Height condition evaluation
   - FSI calculations
   - Training log persistence

3. **`test_geometry.py`** - Geometry Conversion Tests
   - Building geometry creation
   - Spec parsing (multiple formats)
   - JSON to GLB conversion
   - Batch processing
   - File validation

4. **`test_integration.py`** - End-to-End Tests
   - Complete workflow (prompt → geometry)
   - Multi-city integration
   - Feedback loop
   - Error handling

## 🚀 Running Tests

### Install Test Dependencies

```bash
cd streamlit-prompt-runner
pip install -r requirements.txt
```

This installs:
- `pytest` - Test framework
- `pytest-cov` - Code coverage
- `pytest-mock` - Mocking support

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_mcp.py
pytest tests/test_agents.py
pytest tests/test_geometry.py
pytest tests/test_integration.py
```

### Run with Coverage Report

```bash
pytest --cov=. --cov-report=html
```

Then open `htmlcov/index.html` in your browser to see detailed coverage.

### Run with Verbose Output

```bash
pytest -v
```

### Run Specific Test Class or Function

```bash
# Run specific class
pytest tests/test_mcp.py::TestMCPConnectivity

# Run specific test
pytest tests/test_mcp.py::TestMCPConnectivity::test_mcp_server_running
```

## 📊 Test Categories

### Unit Tests
- Individual functions and methods
- Isolated component testing
- Mock external dependencies

### Integration Tests
- Multi-component workflows
- Database interactions (MCP)
- File I/O operations

### End-to-End Tests
- Complete user workflows
- System-wide functionality
- Real-world scenarios

## ⚙️ Configuration

### `conftest.py`
Contains shared pytest fixtures:
- `sample_spec` - Building specification
- `sample_rule` - DCR rule
- `sample_subject` - Test subject for calculator
- `temp_output_dir` - Temporary directories
- `mock_mcp_response` - Mock API responses
- `sample_cities` - Supported cities list

## 📝 Test Requirements

### MCP Server Tests
Some tests require MCP server to be running:

```bash
python mcp_server.py
```

Tests will automatically skip if server is not available.

### Environment Variables
Optional environment variables:
- `MCP_BASE_URL` - MCP server URL (default: http://127.0.0.1:5001/api/mcp)
- `MONGO_URI` - MongoDB connection string
- `MONGO_DB` - MongoDB database name

## ✅ Test Status

| Test File | Tests | Status |
|-----------|-------|--------|
| test_mcp.py | 12 | ✅ Ready |
| test_agents.py | 11 | ✅ Ready |
| test_geometry.py | 17 | ✅ Ready |
| test_integration.py | 10 | ✅ Ready |
| **Total** | **50** | ✅ **Complete** |

## 🎯 Coverage Goals

- **Target Coverage**: 80%+
- **Critical Paths**: 95%+
- **Agents**: 85%+
- **Utils**: 90%+

## 🐛 Debugging Tests

### Run Failed Tests Only

```bash
pytest --lf
```

### Stop on First Failure

```bash
pytest -x
```

### Show Print Statements

```bash
pytest -s
```

### Run Tests in Parallel (faster)

```bash
pip install pytest-xdist
pytest -n auto
```

## 📚 Best Practices

1. **Mock External Services** - Use mocks for MCP, file I/O
2. **Use Fixtures** - Share common test data via conftest.py
3. **Descriptive Names** - Test names should describe what they test
4. **Arrange-Act-Assert** - Structure tests clearly
5. **Independent Tests** - Each test should run independently
6. **Clean Up** - Use tmp_path for temporary files

## 🔍 Common Issues

### MCP Server Not Running
**Error**: Connection refused
**Solution**: Start MCP server with `python mcp_server.py`

### Import Errors
**Error**: Module not found
**Solution**: Run from project root: `cd streamlit-prompt-runner`

### File Permission Errors
**Error**: Permission denied
**Solution**: Tests use `tmp_path` fixture for temp files

## 📈 Adding New Tests

1. Create test in appropriate file or new file
2. Use fixtures from `conftest.py`
3. Follow naming convention: `test_*.py`
4. Run tests to verify
5. Update this README

## 🎓 Example Test

```python
def test_example(sample_spec):
    """Test description"""
    # Arrange
    input_data = sample_spec
    
    # Act
    result = some_function(input_data)
    
    # Assert
    assert result is not None
    assert result["status"] == "success"
```

## 🚀 CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run Tests
  run: |
    pip install -r requirements.txt
    pytest --cov=. --cov-report=xml
```

### Local Pre-commit Hook

```bash
#!/bin/bash
pytest
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

---

**Last Updated**: November 5, 2025
**Total Tests**: 50
**Coverage Target**: 80%+
