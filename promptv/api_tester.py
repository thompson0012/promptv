"""
API testing with LLM integration for promptv.

Allows testing prompts with real LLM providers to validate behavior.
"""
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel
from promptv.exceptions import PromptVError


class APITestError(PromptVError):
    """Base exception for API testing errors."""
    pass


class TestCase(BaseModel):
    """Single test case for prompt testing."""
    name: str
    variables: Dict[str, str]
    expected_contains: Optional[List[str]] = None
    expected_not_contains: Optional[List[str]] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


class TestResult(BaseModel):
    """Result of a single test case."""
    test_name: str
    passed: bool
    prompt_sent: str
    response: str
    tokens_used: int
    cost: float
    duration_ms: int
    errors: List[str]
    timestamp: datetime


class TestSuite(BaseModel):
    """Collection of test cases."""
    name: str
    prompt_name: str
    prompt_version: str
    provider: str
    model: str
    test_cases: List[TestCase]


class APITester:
    """
    API tester for validating prompts with real LLM providers.
    
    Supports testing prompts with different variable combinations
    and validating responses.
    
    Example:
        >>> tester = APITester()
        >>> suite = TestSuite(
        ...     name="greeting-tests",
        ...     prompt_name="greeting-prompt",
        ...     prompt_version="latest",
        ...     provider="openai",
        ...     model="gpt-4",
        ...     test_cases=[
        ...         TestCase(
        ...             name="test-formal",
        ...             variables={"tone": "formal", "name": "Alice"},
        ...             expected_contains=["Dear", "Alice"]
        ...         )
        ...     ]
        ... )
        >>> results = tester.run_test_suite(suite)
    """
    
    def __init__(self):
        """Initialize APITester."""
        self.results_history: List[TestResult] = []
    
    def run_test_suite(
        self,
        suite: TestSuite,
        prompt_manager=None,
        secrets_manager=None
    ) -> List[TestResult]:
        """
        Run a complete test suite.
        
        Args:
            suite: TestSuite to execute
            prompt_manager: PromptManager instance for loading prompts
            secrets_manager: SecretsManager instance for API keys
        
        Returns:
            List of TestResult objects
        
        Raises:
            APITestError: If test execution fails
        """
        if not prompt_manager:
            from promptv.manager import PromptManager
            prompt_manager = PromptManager()
        
        if not secrets_manager:
            from promptv.secrets_manager import SecretsManager
            secrets_manager = SecretsManager()
        
        # Load prompt
        try:
            prompt_content = prompt_manager.get_prompt(
                suite.prompt_name,
                suite.prompt_version
            )
            if not prompt_content:
                raise APITestError(
                    f"Prompt '{suite.prompt_name}' version '{suite.prompt_version}' not found"
                )
        except Exception as e:
            raise APITestError(f"Failed to load prompt: {e}") from e
        
        # Get API key
        try:
            api_key = secrets_manager.get_secret(f"{suite.provider}_api_key")
            if not api_key:
                raise APITestError(
                    f"API key not found for provider '{suite.provider}'. "
                    f"Set it using: promptv secrets set {suite.provider}_api_key"
                )
        except Exception as e:
            raise APITestError(f"Failed to get API key: {e}") from e
        
        # Run each test case
        results = []
        for test_case in suite.test_cases:
            result = self._run_test_case(
                test_case,
                prompt_content,
                suite.provider,
                suite.model,
                api_key
            )
            results.append(result)
            self.results_history.append(result)
        
        return results
    
    def _run_test_case(
        self,
        test_case: TestCase,
        prompt_template: str,
        provider: str,
        model: str,
        api_key: str
    ) -> TestResult:
        """
        Run a single test case.
        
        Args:
            test_case: TestCase to execute
            prompt_template: Prompt template with variables
            provider: LLM provider name
            model: Model name
            api_key: API key for the provider
        
        Returns:
            TestResult object
        """
        from promptv.variable_engine import VariableEngine
        import time
        
        start_time = time.time()
        errors = []
        
        # Render prompt with variables
        var_engine = VariableEngine()
        try:
            is_valid, missing = var_engine.validate_variables(
                prompt_template,
                test_case.variables
            )
            if not is_valid:
                errors.append(f"Missing variables: {', '.join(missing)}")
                return TestResult(
                    test_name=test_case.name,
                    passed=False,
                    prompt_sent="",
                    response="",
                    tokens_used=0,
                    cost=0.0,
                    duration_ms=0,
                    errors=errors,
                    timestamp=datetime.now()
                )
            
            rendered_prompt = var_engine.render(prompt_template, test_case.variables)
        except Exception as e:
            errors.append(f"Failed to render prompt: {str(e)}")
            return TestResult(
                test_name=test_case.name,
                passed=False,
                prompt_sent="",
                response="",
                tokens_used=0,
                cost=0.0,
                duration_ms=0,
                errors=errors,
                timestamp=datetime.now()
            )
        
        # Call LLM API
        try:
            response_text, tokens_used, cost = self._call_llm_api(
                provider=provider,
                model=model,
                api_key=api_key,
                prompt=rendered_prompt,
                max_tokens=test_case.max_tokens,
                temperature=test_case.temperature
            )
        except Exception as e:
            errors.append(f"API call failed: {str(e)}")
            return TestResult(
                test_name=test_case.name,
                passed=False,
                prompt_sent=rendered_prompt,
                response="",
                tokens_used=0,
                cost=0.0,
                duration_ms=int((time.time() - start_time) * 1000),
                errors=errors,
                timestamp=datetime.now()
            )
        
        # Validate response
        passed = True
        
        if test_case.expected_contains:
            for expected in test_case.expected_contains:
                if expected not in response_text:
                    errors.append(f"Expected text not found: '{expected}'")
                    passed = False
        
        if test_case.expected_not_contains:
            for not_expected in test_case.expected_not_contains:
                if not_expected in response_text:
                    errors.append(f"Unexpected text found: '{not_expected}'")
                    passed = False
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return TestResult(
            test_name=test_case.name,
            passed=passed,
            prompt_sent=rendered_prompt,
            response=response_text,
            tokens_used=tokens_used,
            cost=cost,
            duration_ms=duration_ms,
            errors=errors,
            timestamp=datetime.now()
        )
    
    def _call_llm_api(
        self,
        provider: str,
        model: str,
        api_key: str,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> tuple[str, int, float]:
        """
        Call LLM API.
        
        Args:
            provider: Provider name (openai, anthropic, etc.)
            model: Model name
            api_key: API key
            prompt: Prompt text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
        
        Returns:
            Tuple of (response_text, tokens_used, cost)
        
        Raises:
            APITestError: If API call fails
        """
        # Load API base URL from config
        from promptv.config_manager import ConfigManager
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        if provider.lower() == "openai":
            api_base_url = config.llm_providers.openai.api_base_url
            return self._call_openai(api_key, model, prompt, max_tokens, temperature, api_base_url)
        elif provider.lower() == "anthropic":
            api_base_url = config.llm_providers.anthropic.api_base_url
            return self._call_anthropic(api_key, model, prompt, max_tokens, temperature, api_base_url)
        else:
            raise APITestError(f"Unsupported provider: {provider}")
    
    def _call_openai(
        self,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: Optional[int],
        temperature: Optional[float],
        api_base_url: str
    ) -> tuple[str, int, float]:
        """Call OpenAI API."""
        try:
            import openai
        except ImportError:
            raise APITestError(
                "OpenAI SDK not installed. Install with: pip install openai"
            )
        
        client = openai.OpenAI(api_key=api_key, base_url=api_base_url)
        
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            kwargs["temperature"] = temperature
        
        try:
            response = client.chat.completions.create(**kwargs)
            
            response_text = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Estimate cost
            from promptv.cost_estimator import CostEstimator
            estimator = CostEstimator()
            try:
                cost_estimate = estimator.estimate_cost(
                    prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                    completion_tokens=response.usage.completion_tokens if response.usage else 0,
                    model=model,
                    provider="openai"
                )
                cost = cost_estimate.total_cost
            except Exception:
                cost = 0.0
            
            return response_text, tokens_used, cost
        
        except Exception as e:
            raise APITestError(f"OpenAI API call failed: {str(e)}") from e
    
    def _call_anthropic(
        self,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: Optional[int],
        temperature: Optional[float],
        api_base_url: str
    ) -> tuple[str, int, float]:
        """Call Anthropic API."""
        try:
            import anthropic
        except ImportError:
            raise APITestError(
                "Anthropic SDK not installed. Install with: pip install anthropic"
            )
        
        client = anthropic.Anthropic(api_key=api_key, base_url=api_base_url)
        
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or 1024
        }
        
        if temperature is not None:
            kwargs["temperature"] = temperature
        
        try:
            response = client.messages.create(**kwargs)
            
            response_text = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        response_text += block.text
            
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            # Estimate cost
            from promptv.cost_estimator import CostEstimator
            estimator = CostEstimator()
            try:
                cost_estimate = estimator.estimate_cost(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    model=model,
                    provider="anthropic"
                )
                cost = cost_estimate.total_cost
            except Exception:
                cost = 0.0
            
            return response_text, tokens_used, cost
        
        except Exception as e:
            raise APITestError(f"Anthropic API call failed: {str(e)}") from e
    
    def save_results(self, results: List[TestResult], output_file: str) -> None:
        """
        Save test results to a JSON file.
        
        Args:
            results: List of TestResult objects
            output_file: Path to output file
        """
        data = {
            "results": [result.model_dump(mode='json') for result in results],
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
                "total_tokens": sum(r.tokens_used for r in results),
                "total_cost": sum(r.cost for r in results),
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)