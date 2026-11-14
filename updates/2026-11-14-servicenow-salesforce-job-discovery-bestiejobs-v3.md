# ServiceNow & Salesforce Job Discovery Methodology - BESTIEJOB v3

**Date:** 2026-11-14
**Worktree:** bestiejobs-v3
**Author:** Kilo

## Executive Summary

This document outlines the comprehensive methodology developed for discovering high-quality ServiceNow and Salesforce developer jobs targeting Toronto, GTA, and Canada remote locations. The approach combines direct company scanning, job aggregator monitoring, certification-based filtering, and location-specific targeting to ensure relevance and quality.

## Current Methodology Analysis

Based on analysis of existing files (`servicenow_jobs_gemma4_2026-10-30.md`, `servicenow_salesforce_jobs_gemma4_2026-10-30.md`), the current methodology includes:

### ServiceNow Patterns
- **Direct Company Scanning**: ServiceNow careers page, BDO Canada, Huron Consulting, Platform 6, ComTec
- **Aggregator Monitoring**: Remotery, FlexJobs, Dice, Indeed, LinkedIn
- **Certification Filtering**: CSA, CAD, CIS-CSM, CMA, CTA requirements
- **Location Targeting**: Toronto/Remote Canada, Remote USA/Canada hybrid roles

### Salesforce Patterns
- **Direct Company Scanning**: Kicksaw, Decisive Point, Marsh McLennan, Cherokee Federal
- **Aggregator Monitoring**: BuiltIn, NeuraFlash, Indeed, LinkedIn, FlexJobs
- **Certification Filtering**: Admin, PD I, PD II, Advanced Admin requirements
- **Location Targeting**: Remote Canada, Toronto, GTA cities

## New Methodology Implementation

### 1. Multi-Layered Discovery System

The new system implements a structured 5-phase approach:

#### Phase 1: Data Sources Identification
- **ServiceNow Sources**: 10+ sources (5 direct companies + 5 aggregators)
- **Salesforce Sources**: 10+ sources (5 direct companies + 5 aggregators)
- **Prioritization**: Direct company sources weighted higher than aggregators

#### Phase 2: Search Pattern Optimization
- **ServiceNow Keywords**: 6+ core terms with variations
- **Salesforce Keywords**: 6+ core terms with variations
- **Certification Mapping**: Detailed mapping of acronyms to full names
- **Location Expansion**: 22+ Toronto/GTA location variants

#### Phase 3: Quality Filtering
- **Recency Filter**: Jobs posted within last 7 days only
- **Certification Requirement**: Must specify relevant certifications
- **Location Match**: Must match Toronto/GTA/Remote Canada patterns
- **Source Reliability**: Direct company sources prioritized over aggregators

#### Phase 4: SubQ API Integration
- **Document Comparison**: Using SUBQ FREE key (`sk-proj-Xx8AOwoBBEXGOg75H0q4YMcNZ3wVCVUV`) for job similarity analysis
- **Decision Making**: Quality scoring algorithm combining source reliability, certification match, and location specificity
- **Duplicate Detection**: URL-based deduplication across all sources

#### Phase 5: Output Generation
- **JSON Format**: Structured data for BESTIEJOB integration
- **Markdown Reports**: Human-readable summaries
- **CSV Export**: For spreadsheet analysis

### 2. Technical Implementation

#### Core Components
- **JobDiscoveryEngine Class**: Modular, extensible architecture
- **Configuration Management**: Separated configs for ServiceNow/Salesforce
- **Quality Scoring Algorithm**: Weighted scoring based on source priority, certification match, and location specificity
- **Duplicate Removal**: URL-based deduplication

#### Key Files Created
- `tools/servicenow_salesforce_job_discovery.py`: Main discovery engine
- `tools/job_discovery_config.py`: Configuration management
- `plans/servicenow-salesforce-job-discovery-plan.md`: Comprehensive methodology plan

### 3. Toronto/GTA Location Strategy

The methodology specifically targets Toronto and GTA locations through:

- **22+ Location Variants**: Including "Toronto", "Remote Canada", "GTA", "Greater Toronto Area", and all major GTA municipalities
- **Hybrid Role Support**: Identifying roles that accept both Toronto-based and Remote Canada candidates
- **Geographic Prioritization**: Higher scores for jobs explicitly mentioning Toronto/GTA cities
- **Remote Canada Focus**: Special handling for fully remote positions available to Canadian residents

### 4. Certification-Based Targeting

The system prioritizes jobs requiring specific certifications:

#### ServiceNow Certifications
- CSA (Certified System Administrator) - Most common requirement
- CAD (Certified Application Developer) - Second most common
- CIS-CSM (Customer Service Management) - For CSM-focused roles
- CMA/CTA (Master/Technical Architect) - For senior architecture roles

#### Salesforce Certifications
- Admin (Administrator) - Most common requirement
- PD I (Platform Developer I) - For development roles
- PD II (Platform Developer II) - For senior development roles
- Advanced Admin - For complex administration roles

### 5. Implementation Status

✅ **Methodology Documented**: Complete 5-phase approach
✅ **Technical Implementation**: Python engine with configuration system
✅ **SubQ Integration**: Configured with available free API key
✅ **Toronto/GTA Focus**: Comprehensive location targeting implemented
✅ **Certification Mapping**: Detailed certification-to-role mapping

## Next Steps

1. **Integration Testing**: Connect with actual web scraping libraries
2. **Production Deployment**: Set up scheduled hourly/daily scans
3. **BESTIEJOB Integration**: Feed results into existing job display system
4. **Performance Optimization**: Add caching and parallel processing
5. **Monitoring System**: Implement health checks and failure alerts

## Conclusion

This methodology provides a robust, scalable approach to discovering ServiceNow and Salesforce developer jobs in the Toronto/GTA market. By combining direct company scanning with aggregator monitoring, certification-based filtering, and location-specific targeting, the system ensures high-quality, relevant job matches while leveraging the available SUBQ API capabilities.

---
*Generated by Kilo on 2026-11-14 at 08:07:13*