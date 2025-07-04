# Configuration Guide

## Overview

The Ansible Inventory Management System is configured through a single YAML file: `inventory-config.yml` in the project root. This file controls all aspects of the system behavior, from environment definitions to file naming patterns.

## Quick Start

1. **Copy the template:**
   ```bash
   cp inventory-config.yml.example inventory-config.yml
   ```

2. **Edit the configuration:**
   ```bash
   nano inventory-config.yml
   ```

3. **Validate the configuration:**
   ```bash
   python -c "import scripts.core.config as config; config.print_configuration_status()"
   ```

4. **Test the system:**
   ```bash
   python scripts/ansible_inventory_cli.py validate
   ```

## Configuration Structure

### Core Sections

| Section | Description | Required |
|---------|-------------|----------|
| `paths` | File and directory paths | Yes |
| `data` | CSV configuration and headers | Yes |
| `environments` | Supported environments | Yes |
| `hosts` | Host validation and settings | Yes |
| `groups` | Group naming patterns | Yes |
| `patch_management` | Patch windows and schedules | No |
| `cmdb` | CMDB integration settings | No |
| `formats` | File formats and patterns | No |
| `logging` | Logging configuration | No |

### Environment Configuration

```yaml
environments:
  supported:
    - production
    - development
    - test
    - acceptance
    - staging     # Add custom environments
  codes:
    production: "prd"
    development: "dev"
    test: "tst"
    acceptance: "acc"
    staging: "stg"  # Add codes for custom environments
```

### CSV Header Configuration

The `data.csv_template_headers` section defines the expected CSV structure:

```yaml
data:
  csv_template_headers:
    - hostname          # Optional when using cname as inventory_key
    - environment       # Required
    - status           # Required
    - cname            # Optional when using hostname as inventory_key, Required when using cname as inventory_key
    - instance         # Optional
    - site_code       # Optional
    # ... add your custom fields
```

**Important:** These headers must match your actual CSV file exactly.

### Host Configuration

```yaml
hosts:
  valid_status_values:
    - active
    - decommissioned
    - maintenance      # Add custom statuses
  
  inventory_key: "hostname"  # or "cname"
  
  grace_periods:
    production: 90
    staging: 30        # Add for custom environments
```

### Inventory Key Configuration

The `inventory_key` setting determines which field is used as the primary identifier:

- **`"hostname"`**: Uses hostname as primary key, with cname as fallback if hostname is empty
- **`"cname"`**: Uses cname as primary key, with hostname as fallback if cname is empty

**Field Requirements:**
- When `inventory_key: "hostname"`: hostname is preferred but optional, cname is optional
- When `inventory_key: "cname"`: cname is preferred but optional, hostname is optional  
- **At least one** of hostname or cname must always be provided for each host

This allows you to:
- Use CNAMEs as primary identifiers when you have a DNS-centric infrastructure
- Fall back gracefully when only one identifier is available
- Maintain backward compatibility with hostname-based configurations

### Multi-Product Support

The system supports multiple products per host by using comma-separated values in the `product_id` field:

```csv
hostname,environment,status,cname,instance,site_code,ssl_port,application_service,product_id,primary_application,function,batch_number,patch_mode,dashboard_group,decommission_date
idm01-prd,production,active,idm01.company.com,1,datacenter-east,636,identity_management,"edirectory,netiq_idm",NetIQ IDM,directory,1,manual,identity-servers,
web01-prd,production,active,web01.company.com,1,datacenter-east,443,web_server,nginx,nginx,frontend,1,auto,web-servers,
```

**Features:**
- **Multiple Products**: Use comma-separated values like `"edirectory,netiq_idm,ldap_proxy"`
- **Product Groups**: Automatically creates inventory groups for each product (e.g., `product_edirectory`, `product_netiq_idm`)
- **Product Queries**: Query hosts by specific products using Ansible patterns
- **Structured Data**: Host vars include detailed product information

**Generated Inventory Groups:**
```yaml
product_edirectory:
  hosts:
    idm01-prd: null
    idm02-prd: null

product_netiq_idm:
  hosts:
    idm01-prd: null
    idm02-prd: null
    idm03-prd: null
```

**Generated Host Vars:**
```yaml
# host_vars/idm01-prd.yml
product_id: "edirectory,netiq_idm"
products:
  installed: ["edirectory", "netiq_idm"]
  primary: "edirectory"
  count: 2
```

## Environment Variable Overrides

Override any configuration value using environment variables:

```bash
# Override CSV file location
export INVENTORY_CSV_FILE="/path/to/custom/hosts.csv"

# Override logging level
export INVENTORY_LOG_LEVEL="DEBUG"

# Override inventory key preference
export INVENTORY_KEY="cname"

# Override support group
export INVENTORY_SUPPORT_GROUP="DevOps Team"
```

## Common Customizations

### Adding New Environments

1. **Add to supported list:**
   ```yaml
   environments:
     supported:
       - production
       - staging      # New environment
       - development
   ```

2. **Add environment code:**
   ```yaml
   environments:
     codes:
       staging: "stg"  # New environment code
   ```

3. **Add grace period:**
   ```yaml
   hosts:
     grace_periods:
       staging: 21     # 3 weeks
   ```

### Custom CSV Fields

1. **Add to header list:**
   ```yaml
   data:
     csv_template_headers:
       - hostname
       - environment
       - status
       - custom_field1    # Your custom field
       - custom_field2    # Another custom field
   ```

2. **Update your CSV file** to include the new columns.

3. **Regenerate inventories:**
   ```bash
   python scripts/ansible_inventory_cli.py generate
   ```

### Custom Group Prefixes

```yaml
groups:
  prefixes:
    application: "app_"
    product: "prod_"      # Changed from "product_"
    environment: "env_"
    location: "loc_"      # New group type
    team: "team_"         # New group type
```

### Custom Patch Windows

```yaml
patch_management:
  windows:
    batch_1: "Saturday 02:00-04:00 UTC"
    emergency: "Daily 01:00-02:00 UTC"      # New batch
    weekend: "Sunday 06:00-08:00 UTC"       # New batch
```

## Feature Flags

Control system functionality with feature flags:

```yaml
features:
  geographic_validation: true     # Enable location validation
  patch_management: true          # Enable patch management
  lifecycle_management: true      # Enable host lifecycle
  backup_on_generate: false       # Auto-backup before generation
  strict_validation: false        # Enable strict mode
  cmdb_integration: true          # Custom feature flag
```

## Organization-Specific Settings

### CMDB Integration

```yaml
cmdb:
  default_support_group: "Your Support Team"
  default_owner: "Infrastructure Team"
  ticket_system_url: "https://tickets.company.com"
  change_approval_required: true
```

### File Headers

```yaml
headers:
  auto_generated: "AUTO-GENERATED BY COMPANY INFRASTRUCTURE TEAM"
  host_vars: "Generated from Company CMDB - Do not edit manually"
  organization: "© 2024 Your Company Name"
```

### Logging

```yaml
logging:
  level: "INFO"          # DEBUG, INFO, WARNING, ERROR
  # For production:
  # level: "WARNING"
  
  # For troubleshooting:
  # level: "DEBUG"
```

## Validation

### Configuration Validation

```bash
# Validate configuration syntax
python scripts/ansible_inventory_cli.py validate

# Test with debug output
python scripts/ansible_inventory_cli.py --log-level DEBUG validate
```

### CSV Structure Validation

The system validates your CSV against the configured headers:

```bash
# Check CSV structure
python scripts/ansible_inventory_cli.py validate

# Output will show:
# ✅ CSV headers match configuration
# ❌ Missing headers: custom_field1
# ⚠️  Unexpected headers: old_field (will be ignored)
```

## Migration from Old Config

If migrating from the old `scripts/core/config.py` approach:

1. **Create new configuration:**
   ```bash
   cp inventory-config.yml.example inventory-config.yml
   ```

2. **Transfer your settings** from the old Python file to the new YAML file.

3. **Test the migration:**
   ```bash
   python scripts/ansible_inventory_cli.py health
   ```

4. **Verify inventory generation:**
   ```bash
   python scripts/ansible_inventory_cli.py generate --dry-run
   ```

## Troubleshooting

### Configuration Not Loading

```bash
# Check if file exists
ls -la inventory-config.yml

# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('inventory-config.yml'))"

# Force reload configuration
python -c "
import scripts.core.config as config
config.reload_config()
print('Configuration reloaded successfully')
"
```

### Environment Variables Not Working

```bash
# Check if variables are set
env | grep INVENTORY_

# Test override
INVENTORY_LOG_LEVEL=DEBUG python scripts/ansible_inventory_cli.py --version
```

### CSV Header Mismatches

```bash
# Check actual CSV headers
head -1 inventory_source/hosts.csv

# Compare with configuration
python -c "
import scripts.core.config as config
print('Configured headers:', config.get_csv_template_headers())
"
```

## Best Practices

1. **Version Control**: Keep `inventory-config.yml` in version control
2. **Environment-Specific**: Use different config files per environment
3. **Documentation**: Comment your custom settings
4. **Testing**: Always test after configuration changes
5. **Backups**: Keep backups of working configurations

## Example Configurations

### Small Organization

```yaml
environments:
  supported: [production, development]
  codes:
    production: "prd"
    development: "dev"

hosts:
  grace_periods:
    production: 30
    development: 7
```

### Enterprise Organization

```yaml
environments:
  supported: [production, staging, testing, development, sandbox]
  codes:
    production: "prd"
    staging: "stg"
    testing: "tst"
    development: "dev"
    sandbox: "sbx"

hosts:
  grace_periods:
    production: 90
    staging: 45
    testing: 21
    development: 7
    sandbox: 3

features:
  strict_validation: true
  backup_on_generate: true
```

For more detailed examples, see the `inventory-config.yml.example` file. 