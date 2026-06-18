def route_task(task_description: str, file_count: int) -> str:
    desc = task_description.lower()
    
    # Highest priority: Criticality and Complexity
    if 'critical' in desc or 'complex' in desc:
        return 'CLOUD_TIER_3'
        
    # Medium priority: File count and architectural keywords
    if file_count > 3 or any(word in desc for word in ['refactor', 'architecture', 'setup']):
        return 'CLOUD_TIER_2'
        
    # Default fallback
    return 'LOCAL_TIER_1'