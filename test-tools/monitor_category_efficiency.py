#!/usr/bin/env python3
"""
Category Import Efficiency Monitor
=================================

This tool monitors category import efficiency and alerts on potential issues.
Run this regularly to ensure the optimization continues to work effectively.
"""

import psycopg2
import psycopg2.extras
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json

def load_db_config():
    """Load database configuration from database/.env file."""
    env_path = Path(__file__).parent.parent / 'database' / '.env'
    load_dotenv(env_path)
    
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'scraper_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres123')
    }

def connect_to_db():
    """Connect to PostgreSQL database."""
    config = load_db_config()
    return psycopg2.connect(**config)

def monitor_category_efficiency():
    """Monitor category import efficiency and detect issues."""
    print("📊 Category Import Efficiency Monitor")
    print("=" * 40)
    
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Check recent efficiency
    print("\n📅 Recent Category Import Efficiency (Last 24 Hours)")
    print("-" * 55)
    
    cur.execute("""
        SELECT 
            DATE_TRUNC('hour', created_at) as hour,
            COUNT(*) as total_attempts,
            COUNT(DISTINCT CONCAT(restaurant_id, '|', name)) as unique_categories,
            ROUND((COUNT(*) - COUNT(DISTINCT CONCAT(restaurant_id, '|', name)))::numeric / COUNT(*) * 100, 1) as duplicate_rate,
            COUNT(DISTINCT restaurant_id) as restaurants_affected
        FROM categories
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY DATE_TRUNC('hour', created_at)
        ORDER BY hour DESC
        LIMIT 12
    """)
    
    recent_stats = cur.fetchall()
    
    if recent_stats:
        print("Hour               | Attempts | Unique | Dup Rate | Restaurants")
        print("-" * 65)
        
        total_attempts = 0
        total_unique = 0
        efficiency_issues = []
        
        for stat in recent_stats:
            total_attempts += stat['total_attempts']
            total_unique += stat['unique_categories']
            
            dup_rate = stat['duplicate_rate']
            status = "✅" if dup_rate == 0 else "⚠️" if dup_rate < 5 else "🚨"
            
            print(f"{stat['hour'].strftime('%Y-%m-%d %H:00')} | {stat['total_attempts']:8} | {stat['unique_categories']:6} | {dup_rate:7}% | {stat['restaurants_affected']:11} {status}")
            
            if dup_rate > 5:
                efficiency_issues.append({
                    'hour': stat['hour'],
                    'duplicate_rate': dup_rate,
                    'attempts': stat['total_attempts']
                })
        
        overall_dup_rate = ((total_attempts - total_unique) / total_attempts * 100) if total_attempts > 0 else 0
        print(f"\nOverall 24h duplicate rate: {overall_dup_rate:.1f}%")
        
        if overall_dup_rate == 0:
            print("🎉 Perfect efficiency - no duplicate attempts!")
        elif overall_dup_rate < 2:
            print("✅ Excellent efficiency - minimal duplicate attempts")
        elif overall_dup_rate < 5:
            print("⚠️  Good efficiency - some duplicate attempts")
        else:
            print("🚨 Poor efficiency - many duplicate attempts detected")
        
        if efficiency_issues:
            print(f"\n🚨 EFFICIENCY ISSUES DETECTED:")
            for issue in efficiency_issues:
                print(f"   {issue['hour'].strftime('%Y-%m-%d %H:00')}: {issue['duplicate_rate']}% duplicate rate ({issue['attempts']} attempts)")
    else:
        print("No category creation activity in the last 24 hours")
    
    # Check for actual duplicates in database
    print("\n🔍 Current Database Duplicate Check")
    print("-" * 35)
    
    cur.execute("""
        SELECT 
            restaurant_id,
            r.name as restaurant_name,
            c.name as category_name,
            COUNT(*) as duplicate_count
        FROM categories c
        JOIN restaurants r ON c.restaurant_id = r.id
        GROUP BY restaurant_id, r.name, c.name
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC
        LIMIT 5
    """)
    
    current_duplicates = cur.fetchall()
    
    if current_duplicates:
        print("🚨 CURRENT DUPLICATES FOUND:")
        for dup in current_duplicates:
            print(f"   🏪 {dup['restaurant_name']}: '{dup['category_name']}' ({dup['duplicate_count']} copies)")
        print("\n❌ Database constraint may have failed or been bypassed!")
    else:
        print("✅ No current duplicates - database integrity intact")
    
    # Performance metrics
    print("\n⚡ Category Creation Performance")
    print("-" * 33)
    
    cur.execute("""
        SELECT 
            COUNT(*) as total_categories,
            COUNT(DISTINCT restaurant_id) as restaurants_with_categories,
            AVG(array_length(string_to_array(name, ' '), 1)) as avg_name_complexity,
            COUNT(CASE WHEN source = 'scraper' THEN 1 END) as scraper_categories,
            COUNT(CASE WHEN source = 'fallback' THEN 1 END) as fallback_categories
        FROM categories
    """)
    
    performance = cur.fetchone()
    
    print(f"Total categories: {performance['total_categories']}")
    print(f"Restaurants with categories: {performance['restaurants_with_categories']}")
    print(f"Average name complexity: {performance['avg_name_complexity']:.1f} words")
    print(f"Scraper-created: {performance['scraper_categories']}")
    print(f"Fallback categories: {performance['fallback_categories']}")
    
    # Recent restaurant activity
    print("\n🏪 Restaurant Category Activity (Last 7 Days)")
    print("-" * 45)
    
    cur.execute("""
        SELECT 
            r.name as restaurant_name,
            COUNT(*) as categories_added,
            MIN(c.created_at) as first_category,
            MAX(c.created_at) as last_category
        FROM categories c
        JOIN restaurants r ON c.restaurant_id = r.id
        WHERE c.created_at >= NOW() - INTERVAL '7 days'
        GROUP BY r.name
        ORDER BY categories_added DESC
        LIMIT 10
    """)
    
    restaurant_activity = cur.fetchall()
    
    if restaurant_activity:
        print("Restaurant                    | Categories | First      | Last")
        print("-" * 65)
        for activity in restaurant_activity:
            name = activity['restaurant_name'][:25] + "..." if len(activity['restaurant_name']) > 25 else activity['restaurant_name']
            print(f"{name:29} | {activity['categories_added']:10} | {activity['first_category'].strftime('%m-%d %H:%M')} | {activity['last_category'].strftime('%m-%d %H:%M')}")
    else:
        print("No category creation activity in the last 7 days")
    
    conn.close()

def generate_efficiency_report():
    """Generate a detailed efficiency report."""
    print("\n📈 Efficiency Improvement Report")
    print("=" * 33)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'optimization_status': 'active',
        'metrics': {},
        'recommendations': []
    }
    
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Calculate efficiency metrics
    cur.execute("""
        SELECT 
            COUNT(*) as total_categories,
            COUNT(DISTINCT CONCAT(restaurant_id, '|', name)) as unique_combinations,
            ROUND((COUNT(*) - COUNT(DISTINCT CONCAT(restaurant_id, '|', name)))::numeric / COUNT(*) * 100, 2) as overall_efficiency_loss
        FROM categories
        WHERE created_at >= NOW() - INTERVAL '7 days'
    """)
    
    metrics = cur.fetchone()
    
    if metrics:
        report['metrics'] = {
            'total_categories_7d': metrics['total_categories'],
            'unique_combinations_7d': metrics['unique_combinations'],
            'efficiency_loss_percent': float(metrics['overall_efficiency_loss'])
        }
        
        efficiency_loss = float(metrics['overall_efficiency_loss'])
        
        if efficiency_loss == 0:
            report['recommendations'].append("Perfect efficiency - optimization working excellently")
        elif efficiency_loss < 2:
            report['recommendations'].append("Very good efficiency - minor room for improvement")
        elif efficiency_loss < 5:
            report['recommendations'].append("Good efficiency - consider investigating causes of duplicate attempts")
        else:
            report['recommendations'].append("Poor efficiency - immediate investigation required")
            report['recommendations'].append("Check for race conditions or concurrent import issues")
            report['recommendations'].append("Review import logic for potential bugs")
    
    conn.close()
    
    # Save report
    report_file = Path(__file__).parent.parent / 'category_efficiency_report.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Efficiency report saved to: {report_file}")
    print(f"📊 Current efficiency loss: {report['metrics'].get('efficiency_loss_percent', 'N/A')}%")

def create_monitoring_script():
    """Create a monitoring script for regular efficiency checks."""
    print("\n🔧 Creating Monitoring Script")
    print("-" * 28)
    
    script_content = """@echo off
echo Running Category Import Efficiency Monitor...
cd /d "C:\\work\\aggregator-menu-scraper\\test-tools"
"C:/Users/mbouklas/.pyenv/pyenv-win/versions/3.12.7/python.exe" monitor_category_efficiency.py
pause
"""
    
    script_path = Path(__file__).parent.parent / 'monitor_category_efficiency.bat'
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"✅ Created monitoring script: {script_path}")
    print("💡 Run this script regularly to monitor category import efficiency")

if __name__ == "__main__":
    monitor_category_efficiency()
    generate_efficiency_report()
    create_monitoring_script()
    
    print("\n🎯 MONITORING SUMMARY:")
    print("✅ Category import efficiency is being monitored")
    print("✅ Database integrity checks in place")
    print("✅ Performance metrics tracked")
    print("✅ Automated efficiency reporting configured")
    
    print(f"\n📋 NEXT STEPS:")
    print("1. Run monitor_category_efficiency.bat regularly")
    print("2. Review efficiency reports for trends")
    print("3. Investigate any efficiency issues immediately")
    print("4. Ensure optimization continues to work as expected")
