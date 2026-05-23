# Plan: MySQL Database Review & Analysis

## Objective
Review two MySQL databases at mysql.50webs.com:
1. `ejaguiar1_stocks` (pw: stocks)
2. `ejaguiar1_backtests` (pw: backtests)

## Goals
- Document each table, its purpose, data types, and relationships
- Identify core tables for predictions per asset class (stocks/crypto/forex/bonds/commodities/ETFs/futures)
- Cross-check data validity for key tables
- Extract insights

## Stage 1 — Parallel Database Exploration
- **Agent 1**: Explore `ejaguiar1_stocks` — list all tables, columns, row counts, sample data
- **Agent 2**: Explore `ejaguiar1_backtests` — list all tables, columns, row counts, sample data

## Stage 2 — Deep Analysis & Cross-Validation
- Analyze schema relationships and prediction pipelines
- Cross-check data validity (date ranges, nulls, consistency, outliers)
- Map tables to asset classes

## Stage 3 — Documentation & Insights
- Produce comprehensive documentation of all tables
- Identify core prediction tables per asset class
- Highlight insights and data quality issues
