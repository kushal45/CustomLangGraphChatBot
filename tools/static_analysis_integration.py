"""
Static Analysis Integration Layer

This module provides the integration layer between the language-agnostic static analysis
framework and the LangGraph workflow nodes. It implements the adapter pattern to bridge
the gap between the analysis framework and the existing node architecture.

Key Features:
- Seamless integration with existing ReviewState
- State tracking and debugging integration
- Error handling and fallback mechanisms
- Performance monitoring and metrics collection

Part of Milestone 3: analyze_code_node Integration & Debugging
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from logging_config import get_logger

from .static_analysis_framework import (
    StaticAnalysisOrchestrator,
    AnalysisConfig,
    RepositoryAnalysisResult,
    AnalysisStatus,
    IssueSeverity
)
from state import ReviewState, ReviewStatus

logger = get_logger(__name__)

# ============================================================================
# INTEGRATION ADAPTER (Adapter Pattern)
# ============================================================================

class StaticAnalysisAdapter:
    """Adapter that integrates static analysis framework with LangGraph workflow."""
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        """Initialize the adapter with configuration."""
        self.config = config or AnalysisConfig()
        self.orchestrator = StaticAnalysisOrchestrator(self.config)
        self.integration_metrics = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'average_execution_time': 0.0
        }
    
    async def analyze_repository_for_node(self, state: ReviewState) -> Dict[str, Any]:
        """
        Analyze repository and return results compatible with LangGraph nodes.
        
        This method serves as the main integration point between the static analysis
        framework and the analyze_code_node.
        """
        start_time = datetime.now()
        analysis_id = None
        
        try:
            # Extract repository information from state
            repository_info = self._extract_repository_info_from_state(state)
            
            # Validate repository information
            if not self._validate_repository_info(repository_info):
                return self._create_error_result("Invalid repository information")
            
            # Execute static analysis
            logger.info(f"Starting static analysis for repository: {repository_info.get('url', 'unknown')}")
            
            analysis_result = await self.orchestrator.analyze_repository(repository_info)
            analysis_id = analysis_result.analysis_id
            
            # Convert results to node-compatible format
            node_result = self._convert_analysis_result_to_node_format(analysis_result, state)
            
            # Update integration metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_success_metrics(execution_time)
            
            logger.info(f"Static analysis completed successfully: {analysis_id}")
            return node_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_failure_metrics(execution_time)
            
            error_msg = f"Static analysis failed: {str(e)}"
            logger.error(f"{error_msg} (analysis_id: {analysis_id})")
            
            return self._create_error_result(error_msg, analysis_id)
    
    def _extract_repository_info_from_state(self, state: ReviewState) -> Dict[str, Any]:
        """Extract repository information from ReviewState."""
        repository_info = state.get('repository_info', {})
        
        # Ensure we have the required structure
        extracted_info = {
            'url': state.get('repository_url', ''),
            'name': repository_info.get('name', 'unknown'),
            'language': repository_info.get('language', 'unknown'),
            'files': repository_info.get('files', []),
            'metadata': {
                'stars': repository_info.get('stars', 0),
                'forks': repository_info.get('forks', 0),
                'description': repository_info.get('description', ''),
                'analysis_timestamp': datetime.now().isoformat()
            }
        }
        
        return extracted_info
    
    def _validate_repository_info(self, repository_info: Dict[str, Any]) -> bool:
        """Validate that repository information is sufficient for analysis."""
        required_fields = ['url', 'files']
        
        for field in required_fields:
            if not repository_info.get(field):
                logger.warning(f"Missing required field for analysis: {field}")
                return False
        
        files = repository_info.get('files', [])
        if not isinstance(files, list) or len(files) == 0:
            logger.warning("No files found for analysis")
            return False
        
        return True
    
    def _convert_analysis_result_to_node_format(
        self, 
        analysis_result: RepositoryAnalysisResult, 
        original_state: ReviewState
    ) -> Dict[str, Any]:
        """Convert analysis framework results to LangGraph node format."""
        
        # Calculate summary statistics
        total_issues = analysis_result.overall_metrics.get('total_issues_found', 0)
        languages_analyzed = len(analysis_result.language_results)
        tools_executed = analysis_result.overall_metrics.get('tools_executed', 0)
        
        # Categorize issues by severity
        issues_by_severity = self._categorize_issues_by_severity(analysis_result)
        
        # Create analysis summary
        analysis_summary = {
            'analysis_id': analysis_result.analysis_id,
            'repository_url': analysis_result.repository_url,
            'timestamp': analysis_result.timestamp,
            'total_issues': total_issues,
            'languages_analyzed': languages_analyzed,
            'tools_executed': tools_executed,
            'issues_by_severity': issues_by_severity,
            'execution_summary': analysis_result.execution_summary
        }
        
        # Create detailed results by language
        language_details = {}
        for language, lang_result in analysis_result.language_results.items():
            language_details[language] = {
                'file_count': lang_result.file_count,
                'total_issues': lang_result.total_issues,
                'tools_used': [tr.tool_name for tr in lang_result.tool_results],
                'tool_results': [
                    {
                        'tool_name': tr.tool_name,
                        'status': tr.status.value,
                        'issues_found': len(tr.issues),
                        'execution_time': tr.execution_time,
                        'error_message': tr.error_message
                    }
                    for tr in lang_result.tool_results
                ],
                'top_issues': self._extract_top_issues(lang_result, limit=10)
            }
        
        # Create recommendations
        recommendations = self._generate_recommendations(analysis_result)
        
        # Return updated state
        updated_state = original_state.copy()
        updated_state.update({
            'current_step': 'generate_report',
            'status': ReviewStatus.ANALYZING_CODE,
            'analysis_results': {
                'static_analysis': {
                    'summary': analysis_summary,
                    'language_details': language_details,
                    'recommendations': recommendations,
                    'raw_results': analysis_result  # For debugging purposes
                }
            },
            'analysis_metadata': {
                'analysis_type': 'static_analysis',
                'framework_version': '1.0.0',
                'integration_version': '1.0.0',
                'analysis_timestamp': datetime.now().isoformat()
            }
        })
        
        return updated_state
    
    def _categorize_issues_by_severity(self, analysis_result: RepositoryAnalysisResult) -> Dict[str, int]:
        """Categorize all issues by severity level."""
        severity_counts = {severity.value: 0 for severity in IssueSeverity}
        
        for lang_result in analysis_result.language_results.values():
            for tool_result in lang_result.tool_results:
                for issue in tool_result.issues:
                    severity_counts[issue.severity.value] += 1
        
        return severity_counts
    
    def _extract_top_issues(self, lang_result, limit: int = 10) -> List[Dict[str, Any]]:
        """Extract top issues for a language."""
        all_issues = []
        
        for tool_result in lang_result.tool_results:
            for issue in tool_result.issues:
                all_issues.append({
                    'tool': tool_result.tool_name,
                    'file_path': issue.file_path,
                    'line_number': issue.line_number,
                    'severity': issue.severity.value,
                    'category': issue.category,
                    'message': issue.message,
                    'rule_id': issue.rule_id,
                    'suggestion': issue.suggestion
                })
        
        # Sort by severity (critical first) and return top issues
        severity_order = {
            IssueSeverity.CRITICAL.value: 0,
            IssueSeverity.HIGH.value: 1,
            IssueSeverity.MEDIUM.value: 2,
            IssueSeverity.LOW.value: 3,
            IssueSeverity.INFO.value: 4
        }
        
        sorted_issues = sorted(
            all_issues, 
            key=lambda x: severity_order.get(x['severity'], 5)
        )
        
        return sorted_issues[:limit]
    
    def _generate_recommendations(self, analysis_result: RepositoryAnalysisResult) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on analysis results."""
        recommendations = []
        
        # Analyze overall code quality
        total_issues = analysis_result.overall_metrics.get('total_issues_found', 0)
        files_analyzed = analysis_result.overall_metrics.get('total_files_analyzed', 1)
        
        issues_per_file = total_issues / files_analyzed if files_analyzed > 0 else 0
        
        if issues_per_file >= 10:
            recommendations.append({
                'type': 'code_quality',
                'priority': 'high',
                'title': 'High Issue Density Detected',
                'description': f'Average of {issues_per_file:.1f} issues per file indicates potential code quality concerns.',
                'action': 'Consider implementing stricter code review processes and automated quality gates.'
            })
        
        # Language-specific recommendations
        for language, lang_result in analysis_result.language_results.items():
            if lang_result.total_issues > 0:
                failed_tools = [tr for tr in lang_result.tool_results if tr.status == AnalysisStatus.FAILED]
                
                if failed_tools:
                    recommendations.append({
                        'type': 'tooling',
                        'priority': 'medium',
                        'title': f'Analysis Tool Issues for {language.title()}',
                        'description': f'Some analysis tools failed for {language} files.',
                        'action': f'Check tool configuration and dependencies for: {", ".join(tr.tool_name for tr in failed_tools)}'
                    })
        
        return recommendations
    
    def _create_error_result(self, error_message: str, analysis_id: Optional[str] = None) -> Dict[str, Any]:
        """Create an error result for failed analysis."""
        return {
            'current_step': 'error_handler',
            'status': ReviewStatus.FAILED,
            'error': {
                'type': 'static_analysis_error',
                'message': error_message,
                'analysis_id': analysis_id,
                'timestamp': datetime.now().isoformat()
            },
            'analysis_results': {
                'static_analysis': {
                    'summary': {
                        'status': 'failed',
                        'error': error_message
                    }
                }
            }
        }
    
    def _update_success_metrics(self, execution_time: float) -> None:
        """Update metrics for successful analysis."""
        self.integration_metrics['total_analyses'] += 1
        self.integration_metrics['successful_analyses'] += 1
        
        # Update average execution time
        total = self.integration_metrics['total_analyses']
        current_avg = self.integration_metrics['average_execution_time']
        self.integration_metrics['average_execution_time'] = (
            (current_avg * (total - 1) + execution_time) / total
        )
    
    def _update_failure_metrics(self, execution_time: float) -> None:
        """Update metrics for failed analysis."""
        self.integration_metrics['total_analyses'] += 1
        self.integration_metrics['failed_analyses'] += 1
        
        # Update average execution time
        total = self.integration_metrics['total_analyses']
        current_avg = self.integration_metrics['average_execution_time']
        self.integration_metrics['average_execution_time'] = (
            (current_avg * (total - 1) + execution_time) / total
        )
    
    def get_integration_metrics(self) -> Dict[str, Any]:
        """Get integration performance metrics."""
        return self.integration_metrics.copy()

# ============================================================================
# CONVENIENCE FUNCTIONS FOR NODE INTEGRATION
# ============================================================================

async def analyze_repository_with_static_analysis(state: ReviewState) -> Dict[str, Any]:
    """
    Convenience function for integrating static analysis into analyze_code_node.
    
    This function can be directly called from the analyze_code_node implementation.
    """
    adapter = StaticAnalysisAdapter()
    return await adapter.analyze_repository_for_node(state)

def create_custom_analysis_config(**kwargs) -> AnalysisConfig:
    """Create a custom analysis configuration."""
    return AnalysisConfig(**kwargs)
