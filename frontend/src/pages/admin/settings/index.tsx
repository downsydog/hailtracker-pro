import { useState } from 'react'
import { Settings, User, Bell, Shield, Database, Key, Save, Clock, Play, AlertTriangle, CheckCircle, Loader2, DollarSign, Plus, Trash2, MapPin, TestTube, Wrench, ChevronRight, Lock } from 'lucide-react'
import {
  useAutoNudgesSettings,
  useUpdateAutoNudges,
  useTestAutoNudges,
  ALERT_TYPE_OPTIONS,
  ROLE_OPTIONS,
  TIMEZONE_OPTIONS,
  type AutoNudgesConfig,
} from '@/hooks/use-auto-nudges'
import {
  useLaborRatesSettings,
  useUpdateLaborRates,
  usePreviewLaborRate,
  US_STATES,
  type LaborRatesConfig,
  type LaborRateRule,
} from '@/hooks/use-labor-rates'
import {
  useRiCatalog,
  useDeleteRIOperation,
  RIOperation,
  RIStep,
} from '@/hooks/use-ri'

const tabs = [
  { id: 'general', label: 'General', icon: Settings },
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'auto-nudges', label: 'Auto-Nudges', icon: Clock },
  { id: 'labor-rates', label: 'Labor Rates', icon: DollarSign },
  { id: 'ri-catalog', label: 'R&I Catalog', icon: Wrench },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'integrations', label: 'Integrations', icon: Database },
  { id: 'api', label: 'API Keys', icon: Key },
]

function AutoNudgesSettings() {
  const { data, isLoading, error } = useAutoNudgesSettings()
  const updateMutation = useUpdateAutoNudges()
  const testMutation = useTestAutoNudges()
  const [localConfig, setLocalConfig] = useState<Partial<AutoNudgesConfig> | null>(null)
  const [localTimezone, setLocalTimezone] = useState<string | null>(null)

  // Initialize local state when data loads
  const config = localConfig ?? data?.config
  const timezone = localTimezone ?? data?.timezone ?? 'America/Chicago'

  const handleToggle = (field: keyof AutoNudgesConfig, value: boolean | string) => {
    setLocalConfig(prev => ({
      ...(prev ?? data?.config ?? {}),
      [field]: value,
    }))
  }

  const handleNestedChange = (
    parent: 'recipients' | 'thresholds' | 'rate_limits',
    field: string,
    value: unknown
  ) => {
    setLocalConfig(prev => {
      const current = prev ?? data?.config ?? {}
      const parentObj = current[parent] ?? data?.config?.[parent] ?? {}
      return {
        ...current,
        [parent]: {
          ...parentObj,
          [field]: value,
        },
      }
    })
  }

  const handleSave = async () => {
    if (!localConfig && !localTimezone) return

    await updateMutation.mutateAsync({
      config: localConfig ?? undefined,
      timezone: localTimezone ?? undefined,
    })

    setLocalConfig(null)
    setLocalTimezone(null)
  }

  const handleTest = () => {
    testMutation.mutate()
  }

  if (isLoading) {
    return (
      <div className="bg-card rounded-lg border p-6">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading auto-nudges settings...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-card rounded-lg border p-6">
        <div className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="h-4 w-4" />
          Failed to load settings: {error.message}
        </div>
      </div>
    )
  }

  const hasChanges = localConfig !== null || localTimezone !== null

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="bg-card rounded-lg border p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold">Auto-Nudges</h2>
            <p className="text-sm text-muted-foreground">
              Automatically send SLA digest emails when escalations reach configured thresholds.
            </p>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <span className="text-sm font-medium">
              {config?.enabled ? 'Enabled' : 'Disabled'}
            </span>
            <input
              type="checkbox"
              checked={config?.enabled ?? false}
              onChange={(e) => handleToggle('enabled', e.target.checked)}
              className="rounded"
            />
          </label>
        </div>

        {config?.dry_run && config?.enabled && (
          <div className="flex items-center gap-2 p-3 bg-amber-50 text-amber-800 rounded-md text-sm">
            <AlertTriangle className="h-4 w-4" />
            Dry run mode is enabled. Emails will be logged but not sent.
          </div>
        )}
      </div>

      {/* Schedule Card */}
      <div className="bg-card rounded-lg border p-6">
        <h3 className="font-semibold mb-4">Schedule</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Frequency</label>
            <select
              value={config?.digest_schedule ?? 'daily'}
              onChange={(e) => handleToggle('digest_schedule', e.target.value)}
              className="w-full px-3 py-2 border rounded-md bg-background"
            >
              <option value="daily">Daily</option>
              <option value="hourly">Hourly</option>
            </select>
          </div>
          {config?.digest_schedule !== 'hourly' && (
            <div>
              <label className="block text-sm font-medium mb-1">Time (Local)</label>
              <input
                type="time"
                value={config?.digest_time_local ?? '08:30'}
                onChange={(e) => handleToggle('digest_time_local', e.target.value)}
                className="w-full px-3 py-2 border rounded-md bg-background"
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">Timezone</label>
            <select
              value={timezone}
              onChange={(e) => setLocalTimezone(e.target.value)}
              className="w-full px-3 py-2 border rounded-md bg-background"
            >
              {TIMEZONE_OPTIONS.map(tz => (
                <option key={tz.value} value={tz.value}>{tz.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Recipients Card */}
      <div className="bg-card rounded-lg border p-6">
        <h3 className="font-semibold mb-4">Recipients</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Mode</label>
            <select
              value={config?.recipients?.mode ?? 'roles'}
              onChange={(e) => handleNestedChange('recipients', 'mode', e.target.value)}
              className="w-full px-3 py-2 border rounded-md bg-background"
            >
              <option value="roles">Send to users with specific roles</option>
              <option value="explicit">Send to specific email addresses</option>
            </select>
          </div>

          {config?.recipients?.mode === 'roles' && (
            <div>
              <label className="block text-sm font-medium mb-2">Roles to notify</label>
              <div className="flex flex-wrap gap-2">
                {ROLE_OPTIONS.map(role => {
                  const isSelected = config?.recipients?.roles?.includes(role.value) ?? false
                  return (
                    <label
                      key={role.value}
                      className={`flex items-center gap-2 px-3 py-1.5 border rounded-md cursor-pointer transition-colors ${
                        isSelected ? 'bg-primary text-primary-foreground border-primary' : 'hover:bg-accent'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => {
                          const current = config?.recipients?.roles ?? []
                          const newRoles = e.target.checked
                            ? [...current, role.value]
                            : current.filter(r => r !== role.value)
                          handleNestedChange('recipients', 'roles', newRoles)
                        }}
                        className="sr-only"
                      />
                      {role.label}
                    </label>
                  )
                })}
              </div>
            </div>
          )}

          {config?.recipients?.mode === 'explicit' && (
            <div>
              <label className="block text-sm font-medium mb-1">Email addresses (one per line)</label>
              <textarea
                value={config?.recipients?.emails?.join('\n') ?? ''}
                onChange={(e) => {
                  const emails = e.target.value.split('\n').filter(Boolean)
                  handleNestedChange('recipients', 'emails', emails)
                }}
                className="w-full px-3 py-2 border rounded-md bg-background h-24"
                placeholder="manager@company.com&#10;owner@company.com"
              />
            </div>
          )}
        </div>
      </div>

      {/* Thresholds Card */}
      <div className="bg-card rounded-lg border p-6">
        <h3 className="font-semibold mb-4">Thresholds</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Digest will be sent if any of these thresholds are met.
        </p>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">Critical (min)</label>
            <input
              type="number"
              min="1"
              value={config?.thresholds?.send_if_at_least?.critical ?? 1}
              onChange={(e) => {
                const current = config?.thresholds?.send_if_at_least ?? {}
                handleNestedChange('thresholds', 'send_if_at_least', {
                  ...current,
                  critical: parseInt(e.target.value) || 1,
                })
              }}
              className="w-full px-3 py-2 border rounded-md bg-background"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">High (min)</label>
            <input
              type="number"
              min="1"
              value={config?.thresholds?.send_if_at_least?.high ?? 2}
              onChange={(e) => {
                const current = config?.thresholds?.send_if_at_least ?? {}
                handleNestedChange('thresholds', 'send_if_at_least', {
                  ...current,
                  high: parseInt(e.target.value) || 2,
                })
              }}
              className="w-full px-3 py-2 border rounded-md bg-background"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Warning (min)</label>
            <input
              type="number"
              min="1"
              value={config?.thresholds?.send_if_at_least?.warn ?? 5}
              onChange={(e) => {
                const current = config?.thresholds?.send_if_at_least ?? {}
                handleNestedChange('thresholds', 'send_if_at_least', {
                  ...current,
                  warn: parseInt(e.target.value) || 5,
                })
              }}
              className="w-full px-3 py-2 border rounded-md bg-background"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Alert types to include</label>
          <div className="flex flex-wrap gap-2">
            {ALERT_TYPE_OPTIONS.map(type => {
              const includeTypes = config?.thresholds?.include_types
              const isAllTypes = includeTypes === null || includeTypes === undefined
              const isSelected = isAllTypes || includeTypes?.includes(type.value)
              return (
                <label
                  key={type.value}
                  className={`flex items-center gap-2 px-3 py-1.5 border rounded-md cursor-pointer transition-colors ${
                    isSelected ? 'bg-primary text-primary-foreground border-primary' : 'hover:bg-accent'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected ?? true}
                    onChange={(e) => {
                      let current = config?.thresholds?.include_types ?? null
                      if (current === null) {
                        // Currently "all" - switching to explicit list
                        current = ALERT_TYPE_OPTIONS.map(t => t.value)
                      }
                      const newTypes = e.target.checked
                        ? [...current, type.value]
                        : current.filter(t => t !== type.value)
                      // If all types selected, set to null for "all"
                      const finalTypes = newTypes.length === ALERT_TYPE_OPTIONS.length ? null : newTypes
                      handleNestedChange('thresholds', 'include_types', finalTypes)
                    }}
                    className="sr-only"
                  />
                  {type.label}
                </label>
              )
            })}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Leave all selected for all alert types.
          </p>
        </div>
      </div>

      {/* Rate Limits Card */}
      <div className="bg-card rounded-lg border p-6">
        <h3 className="font-semibold mb-4">Rate Limits (Anti-Spam)</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Minimum hours between nudges for the same item.
        </p>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">Critical (hours)</label>
            <input
              type="number"
              min="1"
              value={config?.rate_limits?.per_entity_per_type_hours?.critical ?? 12}
              onChange={(e) => {
                const current = config?.rate_limits?.per_entity_per_type_hours ?? {}
                handleNestedChange('rate_limits', 'per_entity_per_type_hours', {
                  ...current,
                  critical: parseInt(e.target.value) || 12,
                })
              }}
              className="w-full px-3 py-2 border rounded-md bg-background"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">High (hours)</label>
            <input
              type="number"
              min="1"
              value={config?.rate_limits?.per_entity_per_type_hours?.high ?? 24}
              onChange={(e) => {
                const current = config?.rate_limits?.per_entity_per_type_hours ?? {}
                handleNestedChange('rate_limits', 'per_entity_per_type_hours', {
                  ...current,
                  high: parseInt(e.target.value) || 24,
                })
              }}
              className="w-full px-3 py-2 border rounded-md bg-background"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Warning (hours)</label>
            <input
              type="number"
              min="1"
              value={config?.rate_limits?.per_entity_per_type_hours?.warn ?? 48}
              onChange={(e) => {
                const current = config?.rate_limits?.per_entity_per_type_hours ?? {}
                handleNestedChange('rate_limits', 'per_entity_per_type_hours', {
                  ...current,
                  warn: parseInt(e.target.value) || 48,
                })
              }}
              className="w-full px-3 py-2 border rounded-md bg-background"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Max items per digest</label>
          <input
            type="number"
            min="1"
            max="100"
            value={config?.rate_limits?.max_emails_per_run ?? 30}
            onChange={(e) => handleNestedChange('rate_limits', 'max_emails_per_run', parseInt(e.target.value) || 30)}
            className="w-32 px-3 py-2 border rounded-md bg-background"
          />
        </div>
      </div>

      {/* Dry Run Card */}
      <div className="bg-card rounded-lg border p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold">Dry Run Mode</h3>
            <p className="text-sm text-muted-foreground">
              When enabled, digests are logged but emails are not actually sent.
            </p>
          </div>
          <input
            type="checkbox"
            checked={config?.dry_run ?? true}
            onChange={(e) => handleToggle('dry_run', e.target.checked)}
            className="rounded"
          />
        </div>
      </div>

      {/* Test Results */}
      {testMutation.data && (
        <div className="bg-card rounded-lg border p-6">
          <h3 className="font-semibold mb-4">Test Results</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              {testMutation.data.would_send ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-amber-600" />
              )}
              <span className={testMutation.data.would_send ? 'text-green-700' : 'text-amber-700'}>
                {testMutation.data.would_send ? 'Would send digest' : 'Would NOT send digest'}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">{testMutation.data.reason}</p>

            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="p-2 bg-red-50 rounded text-center">
                <div className="font-bold text-red-700">{testMutation.data.escalation_counts.critical}</div>
                <div className="text-red-600">Critical</div>
              </div>
              <div className="p-2 bg-amber-50 rounded text-center">
                <div className="font-bold text-amber-700">{testMutation.data.escalation_counts.high}</div>
                <div className="text-amber-600">High</div>
              </div>
              <div className="p-2 bg-yellow-50 rounded text-center">
                <div className="font-bold text-yellow-700">{testMutation.data.escalation_counts.warn}</div>
                <div className="text-yellow-600">Warning</div>
              </div>
            </div>

            {testMutation.data.recipients.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-1">Recipients:</p>
                <p className="text-sm text-muted-foreground">{testMutation.data.recipients.join(', ')}</p>
              </div>
            )}

            {testMutation.data.sample_items.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-1">Sample items:</p>
                <ul className="text-sm text-muted-foreground space-y-1">
                  {testMutation.data.sample_items.slice(0, 5).map((item, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        item.severity === 'critical' ? 'bg-red-100 text-red-700' :
                        item.severity === 'high' ? 'bg-amber-100 text-amber-700' :
                        'bg-yellow-100 text-yellow-700'
                      }`}>
                        {item.severity}
                      </span>
                      {item.title}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={!hasChanges || updateMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {updateMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          Save Changes
        </button>
        <button
          onClick={handleTest}
          disabled={testMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 border rounded-md hover:bg-accent disabled:opacity-50"
        >
          {testMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          Test Configuration
        </button>
      </div>

      {updateMutation.isError && (
        <div className="p-3 bg-red-50 text-red-700 rounded-md text-sm">
          Failed to save: {updateMutation.error?.message}
        </div>
      )}

      {updateMutation.isSuccess && !hasChanges && (
        <div className="p-3 bg-green-50 text-green-700 rounded-md text-sm flex items-center gap-2">
          <CheckCircle className="h-4 w-4" />
          Settings saved successfully
        </div>
      )}
    </div>
  )
}

function LaborRatesSettings() {
  const { data, isLoading, error } = useLaborRatesSettings()
  const updateMutation = useUpdateLaborRates()
  const previewMutation = usePreviewLaborRate()
  const [localConfig, setLocalConfig] = useState<Partial<LaborRatesConfig> | null>(null)
  const [editingRule, setEditingRule] = useState<LaborRateRule | null>(null)
  const [showRuleForm, setShowRuleForm] = useState(false)

  // Test rate state
  const [testState, setTestState] = useState('')
  const [testZip, setTestZip] = useState('')
  const [testDate, setTestDate] = useState('')

  const config = localConfig ?? data?.config
  const hasChanges = localConfig !== null

  const handleSave = async () => {
    if (!localConfig) return

    await updateMutation.mutateAsync(localConfig)
    setLocalConfig(null)
  }

  const handleAddRule = () => {
    const newRule: LaborRateRule = {
      id: `rule_${Date.now()}`,
      name: '',
      country: 'US',
      state: null,
      zip_prefixes: [],
      ri_rate: config?.default_ri_rate ?? 85,
    }
    setEditingRule(newRule)
    setShowRuleForm(true)
  }

  const handleEditRule = (rule: LaborRateRule) => {
    setEditingRule({ ...rule })
    setShowRuleForm(true)
  }

  const handleSaveRule = () => {
    if (!editingRule) return

    const currentRules = localConfig?.rules ?? config?.rules ?? []
    const existingIndex = currentRules.findIndex(r => r.id === editingRule.id)

    const newRules = existingIndex >= 0
      ? currentRules.map((r, i) => i === existingIndex ? editingRule : r)
      : [...currentRules, editingRule]

    setLocalConfig(prev => ({
      ...(prev ?? config ?? {}),
      rules: newRules,
    }))

    setEditingRule(null)
    setShowRuleForm(false)
  }

  const handleDeleteRule = (ruleId: string) => {
    const currentRules = localConfig?.rules ?? config?.rules ?? []
    setLocalConfig(prev => ({
      ...(prev ?? config ?? {}),
      rules: currentRules.filter(r => r.id !== ruleId),
    }))
  }

  const handleTestRate = () => {
    previewMutation.mutate({
      state: testState || undefined,
      zip_code: testZip || undefined,
      date: testDate || undefined,
    })
  }

  if (isLoading) {
    return (
      <div className="bg-card rounded-lg border p-6">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading labor rates settings...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-card rounded-lg border p-6">
        <div className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="h-4 w-4" />
          Failed to load settings: {error.message}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Default Rate Card */}
      <div className="bg-card rounded-lg border p-6">
        <h3 className="font-semibold mb-4">Default R&I Labor Rate</h3>
        <div className="flex items-center gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Rate per hour</label>
            <div className="flex items-center gap-2">
              <span className="text-lg">$</span>
              <input
                type="number"
                min="0"
                max="500"
                step="0.01"
                value={config?.default_ri_rate ?? 85}
                onChange={(e) => setLocalConfig(prev => ({
                  ...(prev ?? config ?? {}),
                  default_ri_rate: parseFloat(e.target.value) || 85,
                }))}
                className="w-32 px-3 py-2 border rounded-md bg-background"
              />
              <span className="text-muted-foreground">/hr</span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Currency</label>
            <select
              value={config?.currency ?? 'USD'}
              onChange={(e) => setLocalConfig(prev => ({
                ...(prev ?? config ?? {}),
                currency: e.target.value as 'USD' | 'CAD',
              }))}
              className="px-3 py-2 border rounded-md bg-background"
            >
              <option value="USD">USD</option>
              <option value="CAD">CAD</option>
            </select>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          This rate is used when no regional rules match the estimate location.
        </p>
      </div>

      {/* Regional Rules Card */}
      <div className="bg-card rounded-lg border p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold">Regional Rate Rules</h3>
            <p className="text-sm text-muted-foreground">
              Set different rates based on state, ZIP code, or date ranges.
            </p>
          </div>
          <button
            onClick={handleAddRule}
            className="flex items-center gap-2 px-3 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            Add Rule
          </button>
        </div>

        {(config?.rules?.length ?? 0) === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <MapPin className="h-12 w-12 mx-auto mb-2 opacity-30" />
            <p>No regional rules configured</p>
            <p className="text-sm">All estimates will use the default rate.</p>
          </div>
        ) : (
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="text-left px-4 py-2">Name</th>
                  <th className="text-left px-4 py-2">Location</th>
                  <th className="text-left px-4 py-2">Date Range</th>
                  <th className="text-right px-4 py-2">Rate</th>
                  <th className="text-right px-4 py-2 w-24">Actions</th>
                </tr>
              </thead>
              <tbody>
                {config?.rules?.map((rule) => (
                  <tr key={rule.id} className="border-t">
                    <td className="px-4 py-3 font-medium">{rule.name}</td>
                    <td className="px-4 py-3">
                      <div className="text-sm">
                        {rule.state && <span className="mr-2">{rule.state}</span>}
                        {rule.zip_prefixes && rule.zip_prefixes.length > 0 && (
                          <span className="text-muted-foreground">
                            ZIP: {rule.zip_prefixes.join(', ')}
                          </span>
                        )}
                        {!rule.state && (!rule.zip_prefixes || rule.zip_prefixes.length === 0) && (
                          <span className="text-muted-foreground">{rule.country || 'US'}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {rule.effective_from || rule.effective_to ? (
                        <>
                          {rule.effective_from || '...'} - {rule.effective_to || '...'}
                        </>
                      ) : (
                        'Always'
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono">
                      ${rule.ri_rate.toFixed(2)}/hr
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleEditRule(rule)}
                        className="text-blue-600 hover:text-blue-800 mr-2"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteRule(rule.id)}
                        className="text-red-600 hover:text-red-800"
                      >
                        <Trash2 className="h-4 w-4 inline" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Rule Form Modal */}
      {showRuleForm && editingRule && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg border p-6 w-full max-w-md">
            <h3 className="font-semibold mb-4">
              {config?.rules?.some(r => r.id === editingRule.id) ? 'Edit' : 'Add'} Rate Rule
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Rule Name *</label>
                <input
                  type="text"
                  value={editingRule.name}
                  onChange={(e) => setEditingRule({ ...editingRule, name: e.target.value })}
                  placeholder="e.g., Houston Metro"
                  className="w-full px-3 py-2 border rounded-md bg-background"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">State</label>
                  <select
                    value={editingRule.state ?? ''}
                    onChange={(e) => setEditingRule({ ...editingRule, state: e.target.value || null })}
                    className="w-full px-3 py-2 border rounded-md bg-background"
                  >
                    <option value="">Any State</option>
                    {US_STATES.map(s => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">R&I Rate *</label>
                  <div className="flex items-center gap-1">
                    <span>$</span>
                    <input
                      type="number"
                      min="0"
                      max="500"
                      step="0.01"
                      value={editingRule.ri_rate}
                      onChange={(e) => setEditingRule({ ...editingRule, ri_rate: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3 py-2 border rounded-md bg-background"
                    />
                    <span>/hr</span>
                  </div>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">ZIP Prefixes (comma separated)</label>
                <input
                  type="text"
                  value={editingRule.zip_prefixes?.join(', ') ?? ''}
                  onChange={(e) => {
                    const prefixes = e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                    setEditingRule({ ...editingRule, zip_prefixes: prefixes })
                  }}
                  placeholder="e.g., 77, 78, 79"
                  className="w-full px-3 py-2 border rounded-md bg-background"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  ZIP prefixes for more specific matching (e.g., 77 matches 77001-77999)
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Effective From</label>
                  <input
                    type="date"
                    value={editingRule.effective_from ?? ''}
                    onChange={(e) => setEditingRule({ ...editingRule, effective_from: e.target.value || null })}
                    className="w-full px-3 py-2 border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Effective To</label>
                  <input
                    type="date"
                    value={editingRule.effective_to ?? ''}
                    onChange={(e) => setEditingRule({ ...editingRule, effective_to: e.target.value || null })}
                    className="w-full px-3 py-2 border rounded-md bg-background"
                  />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => { setShowRuleForm(false); setEditingRule(null) }}
                className="px-4 py-2 border rounded-md hover:bg-accent"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveRule}
                disabled={!editingRule.name || editingRule.ri_rate <= 0}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
              >
                Save Rule
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Test Rate Card */}
      <div className="bg-card rounded-lg border p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <TestTube className="h-4 w-4" />
          Test Rate Resolution
        </h3>
        <div className="grid grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">State</label>
            <select
              value={testState}
              onChange={(e) => setTestState(e.target.value)}
              className="w-full px-3 py-2 border rounded-md bg-background"
            >
              <option value="">Any</option>
              {US_STATES.map(s => (
                <option key={s.value} value={s.value}>{s.value}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">ZIP Code</label>
            <input
              type="text"
              value={testZip}
              onChange={(e) => setTestZip(e.target.value)}
              placeholder="77001"
              className="w-full px-3 py-2 border rounded-md bg-background"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Date</label>
            <input
              type="date"
              value={testDate}
              onChange={(e) => setTestDate(e.target.value)}
              className="w-full px-3 py-2 border rounded-md bg-background"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleTestRate}
              disabled={previewMutation.isPending}
              className="px-4 py-2 border rounded-md hover:bg-accent"
            >
              {previewMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Test'
              )}
            </button>
          </div>
        </div>
        {previewMutation.data && (
          <div className="p-4 bg-muted/50 rounded-md">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm text-muted-foreground">Resolved Rate:</span>
                <span className="ml-2 text-lg font-bold">${previewMutation.data.rate.toFixed(2)}/hr</span>
              </div>
              <div className="text-sm">
                <span className={`px-2 py-1 rounded ${
                  previewMutation.data.source === 'rule' ? 'bg-blue-100 text-blue-700' :
                  previewMutation.data.source === 'override' ? 'bg-amber-100 text-amber-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {previewMutation.data.source === 'rule' && previewMutation.data.rule_name
                    ? `Rule: ${previewMutation.data.rule_name}`
                    : previewMutation.data.source === 'override'
                    ? 'Override'
                    : 'Default Rate'}
                </span>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-2">{previewMutation.data.reason}</p>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={!hasChanges || updateMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {updateMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          Save Changes
        </button>
      </div>

      {updateMutation.isError && (
        <div className="p-3 bg-red-50 text-red-700 rounded-md text-sm">
          Failed to save: {updateMutation.error?.message}
        </div>
      )}

      {updateMutation.isSuccess && !hasChanges && (
        <div className="p-3 bg-green-50 text-green-700 rounded-md text-sm flex items-center gap-2">
          <CheckCircle className="h-4 w-4" />
          Settings saved successfully
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Stage 6H-C: R&I Catalog Settings
// =============================================================================

function RICatalogSettings() {
  const { data: catalog, isLoading, error } = useRiCatalog()
  const deleteOperation = useDeleteRIOperation()
  const [expandedOps, setExpandedOps] = useState<Set<number>>(new Set())

  const toggleExpand = (opId: number) => {
    setExpandedOps(prev => {
      const next = new Set(prev)
      if (next.has(opId)) {
        next.delete(opId)
      } else {
        next.add(opId)
      }
      return next
    })
  }

  if (isLoading) {
    return (
      <div className="bg-card rounded-lg border p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-card rounded-lg border p-6">
        <div className="text-red-600">Failed to load R&I catalog</div>
      </div>
    )
  }

  const operations = catalog?.operations || []
  const groupedOps = {
    interior: operations.filter((op: RIOperation) => op.category === 'interior'),
    exterior: operations.filter((op: RIOperation) => op.category === 'exterior'),
    structural: operations.filter((op: RIOperation) => op.category === 'structural'),
  }

  return (
    <div className="bg-card rounded-lg border p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">R&I Catalog</h2>
        <p className="text-sm text-muted-foreground">
          View and manage R&I operations. Seeded operations cannot be deleted.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-3 bg-muted/50 rounded-lg">
          <div className="text-2xl font-bold">{operations.length}</div>
          <div className="text-xs text-muted-foreground">Total Operations</div>
        </div>
        <div className="p-3 bg-blue-50 rounded-lg">
          <div className="text-2xl font-bold text-blue-600">{groupedOps.interior.length}</div>
          <div className="text-xs text-muted-foreground">Interior</div>
        </div>
        <div className="p-3 bg-green-50 rounded-lg">
          <div className="text-2xl font-bold text-green-600">{groupedOps.exterior.length}</div>
          <div className="text-xs text-muted-foreground">Exterior</div>
        </div>
        <div className="p-3 bg-orange-50 rounded-lg">
          <div className="text-2xl font-bold text-orange-600">{groupedOps.structural.length}</div>
          <div className="text-xs text-muted-foreground">Structural</div>
        </div>
      </div>

      {/* Operations by Category */}
      {(['interior', 'exterior', 'structural'] as const).map(category => (
        <div key={category}>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            {category} ({groupedOps[category].length})
          </h3>
          <div className="space-y-2">
            {groupedOps[category].map((op: RIOperation) => {
              const isExpanded = expandedOps.has(op.id)
              const highSteps = (op.steps || []).filter((s: RIStep) => s.denial_resistance === 'high').length
              const totalSteps = (op.steps || []).length

              return (
                <div key={op.id} className="border rounded-lg overflow-hidden">
                  {/* Operation Header */}
                  <div
                    className="flex items-center justify-between p-3 bg-muted/30 cursor-pointer hover:bg-muted/50"
                    onClick={() => toggleExpand(op.id)}
                  >
                    <div className="flex items-center gap-3">
                      <ChevronRight className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          {op.display_name}
                          {op.is_seeded && (
                            <span title="System operation (cannot be deleted)">
                              <Lock className="h-3 w-3 text-muted-foreground" />
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {op.code} • {totalSteps} steps • {highSteps} high resistance
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        op.risk_level === 'high' ? 'bg-red-100 text-red-700' :
                        op.risk_level === 'medium' ? 'bg-amber-100 text-amber-700' :
                        'bg-green-100 text-green-700'
                      }`}>
                        {op.risk_level}
                      </span>
                      {!op.is_seeded && (
                        <button
                          className="p-1 text-red-500 hover:bg-red-50 rounded"
                          onClick={(e) => {
                            e.stopPropagation()
                            if (confirm('Delete this operation?')) {
                              deleteOperation.mutate(op.id)
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Expanded Steps */}
                  {isExpanded && (
                    <div className="p-3 border-t bg-white">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-muted-foreground">
                            <th className="pb-2">Step</th>
                            <th className="pb-2 text-center w-20">Required</th>
                            <th className="pb-2 text-center w-24">Resistance</th>
                            <th className="pb-2 text-right w-20">Hours</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(op.steps || []).map((step: RIStep) => (
                            <tr key={step.id} className="border-t">
                              <td className="py-2">
                                <div className="font-medium">{step.label}</div>
                                {step.risk_tags?.length > 0 && (
                                  <div className="text-xs text-muted-foreground">
                                    Tags: {step.risk_tags.join(', ')}
                                  </div>
                                )}
                              </td>
                              <td className="text-center py-2">
                                {step.required ? (
                                  <CheckCircle className="h-4 w-4 text-green-600 mx-auto" />
                                ) : (
                                  <span className="text-muted-foreground">-</span>
                                )}
                              </td>
                              <td className="text-center py-2">
                                <span className={`text-xs px-2 py-0.5 rounded ${
                                  step.denial_resistance === 'high' ? 'bg-green-100 text-green-700' :
                                  step.denial_resistance === 'medium' ? 'bg-amber-100 text-amber-700' :
                                  'bg-red-100 text-red-700'
                                }`}>
                                  {step.denial_resistance}
                                </span>
                              </td>
                              <td className="text-right py-2 font-mono">
                                {step.base_time_hours?.toFixed(2)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )
            })}
            {groupedOps[category].length === 0 && (
              <div className="text-sm text-muted-foreground py-2">
                No {category} operations
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general')

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account and application settings</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-48 space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-left transition-colors ${
                  activeTab === tab.id
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-accent text-muted-foreground hover:text-foreground'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            )
          })}
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === 'general' && (
            <div className="bg-card rounded-lg border p-6">
              <h2 className="text-lg font-semibold mb-4">General Settings</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Company Name</label>
                  <input
                    type="text"
                    defaultValue="HailTracker Pro"
                    className="w-full px-3 py-2 border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Timezone</label>
                  <select className="w-full px-3 py-2 border rounded-md bg-background">
                    <option>America/Chicago (CST)</option>
                    <option>America/New_York (EST)</option>
                    <option>America/Los_Angeles (PST)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Date Format</label>
                  <select className="w-full px-3 py-2 border rounded-md bg-background">
                    <option>MM/DD/YYYY</option>
                    <option>DD/MM/YYYY</option>
                    <option>YYYY-MM-DD</option>
                  </select>
                </div>
                <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
                  <Save className="h-4 w-4" />
                  Save Changes
                </button>
              </div>
            </div>
          )}

          {activeTab === 'profile' && (
            <div className="bg-card rounded-lg border p-6">
              <h2 className="text-lg font-semibold mb-4">Profile Settings</h2>
              <div className="space-y-4">
                <div className="flex items-center gap-4 mb-6">
                  <div className="h-16 w-16 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xl font-bold">
                    A
                  </div>
                  <button className="px-3 py-1 border rounded-md text-sm hover:bg-accent">
                    Change Photo
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">First Name</label>
                    <input
                      type="text"
                      defaultValue="Admin"
                      className="w-full px-3 py-2 border rounded-md bg-background"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Last Name</label>
                    <input
                      type="text"
                      defaultValue="User"
                      className="w-full px-3 py-2 border rounded-md bg-background"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Email</label>
                  <input
                    type="email"
                    defaultValue="admin@hailtracker.com"
                    className="w-full px-3 py-2 border rounded-md bg-background"
                  />
                </div>
                <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
                  <Save className="h-4 w-4" />
                  Save Changes
                </button>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="bg-card rounded-lg border p-6">
              <h2 className="text-lg font-semibold mb-4">Notification Settings</h2>
              <div className="space-y-4">
                {[
                  { label: 'Email notifications for new leads', defaultChecked: true },
                  { label: 'SMS alerts for hail events', defaultChecked: true },
                  { label: 'Daily summary email', defaultChecked: false },
                  { label: 'Job status updates', defaultChecked: true },
                ].map((item) => (
                  <label key={item.label} className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      defaultChecked={item.defaultChecked}
                      className="rounded border-gray-300"
                    />
                    <span>{item.label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'auto-nudges' && <AutoNudgesSettings />}

          {activeTab === 'labor-rates' && <LaborRatesSettings />}

          {activeTab === 'ri-catalog' && <RICatalogSettings />}

          {['security', 'integrations', 'api'].includes(activeTab) && (
            <div className="bg-card rounded-lg border p-6">
              <h2 className="text-lg font-semibold mb-4 capitalize">{activeTab} Settings</h2>
              <p className="text-muted-foreground">Settings for {activeTab} coming soon.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
