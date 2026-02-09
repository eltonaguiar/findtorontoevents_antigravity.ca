import React, { useState, useEffect, useCallback, useRef } from 'react';
import './AccountabilityDashboard.css';

// Types
interface Task {
  id: number;
  task_template: string;
  custom_name: string | null;
  success_criteria: string | null;
  frequency_type: string;
  target_per_period: number;
  current_streak: number;
  longest_streak: number;
  streak_tier: string;
  shields: number;
  is_paused: boolean;
  recovery_mode: boolean;
  completions_this_period: number;
  period_start: string;
  period_end: string;
  effective_end: string;
  extended_deadline: string | null;
  deadline_pushes_this_period: number;
  deadline_pushes_total: number;
  punishment_text: string | null;
  benefits_text: string | null;
  consequences_text: string | null;
  reminder_time: string;
  created_at: string;
}

interface ScoreBreakdown {
  category: string;
  weight: string;
  score: number;
  points: number;
}

interface ScoreData {
  score: number;
  grade: string;
  breakdown: ScoreBreakdown[];
  explanations: string[];
  tips: string[];
  stats: {
    total_checkins: number;
    total_expected: number;
    active_days: number;
    total_days: number;
    skips: number;
    deadline_pushes: number;
    best_streak: number;
    avg_streak: number;
    tasks_count: number;
  };
}

interface ScoreResponse {
  success: boolean;
  scores: Record<string, ScoreData>;
}

interface Checkin {
  id: number;
  task_id: number;
  task_name: string;
  checkin_time: string;
  notes: string | null;
}

interface HistoryItem {
  id: number;
  type: 'checkin' | 'note';
  note_type?: string;
  text: string | null;
  created_at: string;
  updated_at?: string;
}

interface Identity {
  name: string;
  adherence: number;
  status: 'strong' | 'moderate' | 'needs_attention';
  emoji: string;
}

interface Pattern {
  type: string;
  value: string;
  insight: string;
  confidence: number;
}

interface DashboardData {
  user: {
    discord_user_id: string;
    app_user_id: number | null;
    timezone: string;
    personality_mode: string;
    identity_tags: string | null;
    default_punishment: string | null;
  };
  tasks: Task[];
  recent_checkins: Checkin[];
  identities: Identity[];
  patterns: Pattern[];
  stats: {
    total_checkins: number;
    active_tasks: number;
    on_track: number;
    behind: number;
    total_shields: number;
    highest_streak: number;
  };
}

interface WebNotification {
  id: number;
  type: string;
  title: string;
  body: string;
  is_read: number;
  created_at: string;
}

// Pattern Finder types
interface PatternExample {
  activity_date: string;
  outcome_date: string;
}

interface DetectedPattern {
  id: number;
  activity_task_id: number;
  outcome_task_id: number;
  activity_name: string;
  outcome_name: string;
  lag_days: number;
  confidence: number;
  consistency_pct: number;
  occurrence_count: number;
  exception_count: number;
  total_opportunities: number;
  base_rate_pct: number;
  lift: number;
  summary: string;
  examples: PatternExample[] | null;
  exceptions: PatternExample[] | null;
  status: 'active' | 'dismissed';
  user_rating: 'helpful' | 'not_helpful' | null;
  is_hypothesis: boolean;
  detected_at: string;
}

interface SuperGoalTask {
  task_id: number;
  weight: number;
}

interface SuperGoal {
  id: number;
  name: string;
  description: string | null;
  icon: string;
  tasks: SuperGoalTask[];
  created_at: string;
  updated_at: string;
}

interface ToastItem {
  id: string;
  title: string;
  body: string;
  type: 'info' | 'warning' | 'success' | 'celebration';
  timestamp: number;
}

// Tier configuration
const STREAK_TIERS: Record<string, { emoji: string; color: string; minDays: number }> = {
  none: { emoji: '⚪', color: '#6b7280', minDays: 0 },
  bronze: { emoji: '🥉', color: '#cd7f32', minDays: 7 },
  silver: { emoji: '🥈', color: '#c0c0c0', minDays: 14 },
  gold: { emoji: '🥇', color: '#ffd700', minDays: 30 },
  diamond: { emoji: '💎', color: '#b9f2ff', minDays: 60 },
  savage: { emoji: '🔥', color: '#ff4500', minDays: 90 },
};

// Template display names
const TEMPLATE_NAMES: Record<string, { name: string; emoji: string; category: string }> = {
  gym: { name: 'Gym / Workout', emoji: '🏋️', category: 'fitness' },
  datingappswipesbumble: { name: 'Dating Apps', emoji: '💘', category: 'productivity' },
  cleaning: { name: 'Cleaning', emoji: '🧹', category: 'productivity' },
  meditation: { name: 'Meditation', emoji: '🧘', category: 'mental_health' },
  reading: { name: 'Reading', emoji: '📚', category: 'productivity' },
  leavethehouse: { name: 'Leave the House', emoji: '🚪', category: 'mental_health' },
  gooutside: { name: 'Go Outside', emoji: '🌤️', category: 'mental_health' },
  shower: { name: 'Shower', emoji: '🚿', category: 'self_care' },
  hygiene: { name: 'Personal Hygiene', emoji: '🪥', category: 'self_care' },
  meals: { name: 'Eat Meals', emoji: '🍽️', category: 'self_care' },
  water: { name: 'Drink Water', emoji: '💧', category: 'self_care' },
  medication: { name: 'Take Medication', emoji: '💊', category: 'health' },
  sleep: { name: 'Sleep Schedule', emoji: '😴', category: 'health' },
  socialize: { name: 'Socialize', emoji: '👋', category: 'mental_health' },
  journal: { name: 'Journaling', emoji: '📝', category: 'mental_health' },
  gratitude: { name: 'Gratitude', emoji: '🙏', category: 'mental_health' },
  makebed: { name: 'Make Bed', emoji: '🛏️', category: 'self_care' },
  getdressed: { name: 'Get Dressed', emoji: '👔', category: 'self_care' },
  sunlight: { name: 'Get Sunlight', emoji: '☀️', category: 'health' },
  stretch: { name: 'Stretch', emoji: '🤸', category: 'health' },
};

const CATEGORY_LABELS: Record<string, { label: string; emoji: string }> = {
  fitness: { label: 'Fitness', emoji: '💪' },
  productivity: { label: 'Productivity', emoji: '📈' },
  mental_health: { label: 'Mental Health', emoji: '🧠' },
  self_care: { label: 'Self Care', emoji: '🫧' },
  health: { label: 'Health', emoji: '❤️' },
};

const FREQUENCY_OPTIONS = [
  { value: 'daily', label: 'Daily' },
  { value: 'every2days', label: 'Every 2 Days' },
  { value: 'every3days', label: 'Every 3 Days' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'biweekly', label: 'Every 2 Weeks' },
  { value: 'monthly', label: 'Monthly' },
];

// Default success criteria suggestions per template
const DEFAULT_SUCCESS_CRITERIA: Record<string, string> = {
  gym: 'Did I show up at the gym / complete my workout?',
  datingappswipesbumble: 'Did I do my daily swipes on dating apps?',
  cleaning: 'Did I clean for at least 15 minutes?',
  meditation: 'Did I sit down and meditate today?',
  reading: 'Did I read for at least 15 minutes?',
  leavethehouse: 'Did I leave the house today?',
  gooutside: 'Did I go outside today?',
  shower: 'Did I shower today?',
  hygiene: 'Did I complete my hygiene routine?',
  meals: 'Did I eat a proper meal?',
  water: 'Did I drink a glass of water?',
  medication: 'Did I take my medication on time?',
  sleep: 'Did I stick to my sleep schedule?',
  socialize: 'Did I reach out to someone or socialize today?',
  journal: 'Did I write in my journal today?',
  gratitude: 'Did I practice gratitude today?',
  makebed: 'Did I make my bed this morning?',
  getdressed: 'Did I get dressed today?',
  sunlight: 'Did I get at least 10 minutes of natural sunlight?',
  stretch: 'Did I stretch or move my body today?',
};

function getTaskDisplay(task: Task) {
  const template = TEMPLATE_NAMES[task.task_template];
  if (template) {
    return { name: template.name, emoji: template.emoji };
  }
  return { name: task.custom_name || task.task_template, emoji: '✨' };
}

// Get API base URL
function getApiBase() {
  if (window.location.hostname === 'localhost') {
    return 'http://localhost:8080/fc/api';
  }
  return '/fc/api';
}

// Progress bar component
function ProgressBar({ value, max, color = '#22c55e' }: { value: number; max: number; color?: string }) {
  const percentage = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const isComplete = value >= max;
  
  return (
    <div className="progress-bar-container">
      <div 
        className="progress-bar-fill" 
        style={{ 
          width: `${percentage}%`,
          backgroundColor: isComplete ? '#22c55e' : color
        }}
      />
      <span className="progress-bar-text">{value}/{max}</span>
    </div>
  );
}

// Task card component with success criteria, notes, and history
function TaskCard({ 
  task, onCheckin, onRefresh, isLoading, discordId, appUserId, addToast, defaultPunishment 
}: { 
  task: Task; 
  onCheckin: (taskId: number, notes?: string) => void; 
  onRefresh: () => void;
  isLoading?: boolean;
  discordId: string;
  appUserId: number | null;
  addToast: (title: string, body: string, type?: 'info' | 'warning' | 'success' | 'celebration') => void;
  defaultPunishment: string | null;
}) {
  const { name, emoji } = getTaskDisplay(task);
  const tier = STREAK_TIERS[task.streak_tier] || STREAK_TIERS.none;
  const percentage = task.target_per_period > 0 
    ? Math.round((task.completions_this_period / task.target_per_period) * 100) 
    : 0;
  const isComplete = task.completions_this_period >= task.target_per_period;
  const remaining = Math.max(0, task.target_per_period - task.completions_this_period);
  
  // Local state for expanded panels
  const [showHistory, setShowHistory] = useState(false);
  const [showNoteInput, setShowNoteInput] = useState(false);
  const [showSkipModal, setShowSkipModal] = useState(false);
  const [skipReason, setSkipReason] = useState('other');
  const [skipNotes, setSkipNotes] = useState('');
  const [skipExtendDays, setSkipExtendDays] = useState(1);
  const [skipSubmitting, setSkipSubmitting] = useState(false);
  const [checkinNote, setCheckinNote] = useState('');
  const [newNote, setNewNote] = useState('');
  const [noteSubmitting, setNoteSubmitting] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [editingCriteria, setEditingCriteria] = useState(false);
  const [criteriaText, setCriteriaText] = useState(task.success_criteria || '');
  const [criteriaSaving, setCriteriaSaving] = useState(false);
  const [editingPunishment, setEditingPunishment] = useState(false);
  const [punishmentText, setPunishmentText] = useState(task.punishment_text || '');
  const [punishmentSaving, setPunishmentSaving] = useState(false);
  const [editingBenefits, setEditingBenefits] = useState(false);
  const [benefitsText, setBenefitsText] = useState(task.benefits_text || '');
  const [benefitsSaving, setBenefitsSaving] = useState(false);
  const [editingConsequences, setEditingConsequences] = useState(false);
  const [consequencesText, setConsequencesText] = useState(task.consequences_text || '');
  const [consequencesSaving, setConsequencesSaving] = useState(false);

  const suggestedCriteria = DEFAULT_SUCCESS_CRITERIA[task.task_template] || '';
  const displayCriteria = task.success_criteria || suggestedCriteria;
  const hasCriteria = !!task.success_criteria;

  let statusClass = 'status-behind';
  let statusText = `${remaining} more needed`;
  if (isComplete) {
    statusClass = 'status-complete';
    statusText = 'Complete!';
  } else if (percentage >= 50) {
    statusClass = 'status-on-track';
    statusText = `${remaining} more needed`;
  }

  // Fetch task history
  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      let url = `${getApiBase()}/accountability/task_notes.php?task_id=${task.id}`;
      if (appUserId) url += `&app_user_id=${appUserId}`;
      if (discordId) url += `&discord_id=${discordId}`;
      const response = await fetch(url);
      const result = await response.json();
      if (result.history) {
        setHistory(result.history);
      }
    } catch {
      // silent fail
    } finally {
      setHistoryLoading(false);
    }
  };

  // Toggle history panel
  const handleToggleHistory = () => {
    if (!showHistory) {
      fetchHistory();
    }
    setShowHistory(!showHistory);
  };

  // Save success criteria
  const handleSaveCriteria = async () => {
    setCriteriaSaving(true);
    try {
      const body: Record<string, unknown> = { 
        task_id: task.id, 
        action: 'update_success_criteria',
        success_criteria: criteriaText 
      };
      if (appUserId) body.app_user_id = appUserId;
      if (discordId) body.discord_id = discordId;

      const response = await fetch(`${getApiBase()}/accountability/task_notes.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = await response.json();
      if (result.success) {
        task.success_criteria = criteriaText || null;
        setEditingCriteria(false);
        addToast('Updated!', 'Success criteria saved.', 'success');
      } else {
        addToast('Error', result.error || 'Failed to save', 'warning');
      }
    } catch {
      addToast('Error', 'Failed to save criteria', 'warning');
    } finally {
      setCriteriaSaving(false);
    }
  };

  // Add note
  const handleAddNote = async () => {
    if (!newNote.trim()) return;
    setNoteSubmitting(true);
    try {
      const body: Record<string, unknown> = {
        task_id: task.id,
        action: 'add_note',
        note_text: newNote.trim(),
      };
      if (appUserId) body.app_user_id = appUserId;
      if (discordId) body.discord_id = discordId;

      const response = await fetch(`${getApiBase()}/accountability/task_notes.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = await response.json();
      if (result.success && result.note) {
        setHistory(prev => [result.note, ...prev]);
        setNewNote('');
        setShowNoteInput(false);
        addToast('Note saved!', 'Your note has been added to the task history.', 'success');
      } else {
        addToast('Error', result.error || 'Failed to save note', 'warning');
      }
    } catch {
      addToast('Error', 'Failed to save note', 'warning');
    } finally {
      setNoteSubmitting(false);
    }
  };

  // Handle checkin with optional note
  const handleCheckinClick = () => {
    onCheckin(task.id, checkinNote.trim() || undefined);
    setCheckinNote('');
  };

  // Handle skip with deadline extension
  const handleSkipSubmit = async () => {
    setSkipSubmitting(true);
    try {
      const body: Record<string, unknown> = {
        task_id: task.id,
        reason: skipReason,
        notes: skipNotes.trim() || undefined,
        extend_days: skipExtendDays,
      };
      if (appUserId) body.app_user_id = appUserId;
      if (discordId) body.discord_id = discordId;

      const response = await fetch(`${getApiBase()}/accountability/skip_extend.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = await response.json();
      if (result.success) {
        addToast('Skip Logged', result.message, 'info');
        task.extended_deadline = result.new_deadline;
        task.deadline_pushes_this_period = result.pushes_this_period;
        setShowSkipModal(false);
        setSkipNotes('');
        setSkipReason('other');
        // Trigger parent refresh
        onRefresh(); // Refresh dashboard data
      } else {
        addToast('Error', result.error || 'Failed to log skip', 'warning');
      }
    } catch {
      addToast('Error', 'Failed to log skip', 'warning');
    } finally {
      setSkipSubmitting(false);
    }
  };

  // Handle punishment save
  const handleSavePunishment = async () => {
    setPunishmentSaving(true);
    try {
      const body: Record<string, unknown> = {
        task_id: task.id,
        action: 'update_punishment',
        punishment_text: punishmentText.trim() || null,
      };
      if (appUserId) body.app_user_id = appUserId;
      if (discordId) body.discord_id = discordId;

      const response = await fetch(`${getApiBase()}/accountability/task_notes.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = await response.json();
      if (result.success) {
        task.punishment_text = punishmentText.trim() || null;
        setEditingPunishment(false);
        addToast('Updated!', 'Punishment saved.', 'success');
      } else {
        addToast('Error', result.error || 'Failed to save', 'warning');
      }
    } catch {
      addToast('Error', 'Failed to save punishment', 'warning');
    } finally {
      setPunishmentSaving(false);
    }
  };

  // Generic field saver for benefits/consequences
  const handleSaveField = async (
    action: string, fieldName: string, value: string,
    onSuccess: () => void, setLoading: (v: boolean) => void
  ) => {
    setLoading(true);
    try {
      const body: Record<string, unknown> = { task_id: task.id, action, [fieldName]: value.trim() || null };
      if (appUserId) body.app_user_id = appUserId;
      if (discordId) body.discord_id = discordId;
      const res = await fetch(`${getApiBase()}/accountability/task_notes.php`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      const result = await res.json();
      if (result.success) { onSuccess(); addToast('Saved!', `${fieldName.replace('_text','')} updated.`, 'success'); }
      else { addToast('Error', result.error || 'Failed to save', 'warning'); }
    } catch { addToast('Error', 'Failed to save', 'warning'); }
    finally { setLoading(false); }
  };

  const skipReasonOptions = [
    { value: 'sick', label: 'Sick / Health' },
    { value: 'work', label: 'Work / School' },
    { value: 'family', label: 'Family' },
    { value: 'motivation', label: 'Low Motivation' },
    { value: 'forgot', label: 'Forgot' },
    { value: 'emergency', label: 'Emergency' },
    { value: 'travel', label: 'Travel' },
    { value: 'weather', label: 'Weather' },
    { value: 'other', label: 'Other' },
  ];

  return (
    <div className={`task-card ${task.recovery_mode ? 'recovery-mode' : ''} ${task.is_paused ? 'paused' : ''}`}>
      {task.recovery_mode && <div className="recovery-badge">Recovery Mode</div>}
      {task.is_paused && <div className="paused-badge">Paused</div>}
      
      <div className="task-header">
        <div className="task-title">
          <span className="task-emoji">{emoji}</span>
          <h3>{name}</h3>
        </div>
        <div className="streak-badge" style={{ backgroundColor: `${tier.color}30`, color: tier.color }}>
          {tier.emoji} {task.current_streak} days
        </div>
      </div>

      {/* Success Criteria Section */}
      <div className="success-criteria-section">
        {!editingCriteria ? (
          <div 
            className={`success-criteria-display ${!hasCriteria ? 'suggested' : ''}`}
            onClick={() => { setEditingCriteria(true); setCriteriaText(task.success_criteria || suggestedCriteria); }}
            title="Click to edit success criteria"
          >
            <span className="criteria-icon">{hasCriteria ? '🎯' : '💡'}</span>
            <div className="criteria-content">
              <span className="criteria-label">{hasCriteria ? 'Success Criteria' : 'Add success criteria'}</span>
              <span className="criteria-text">{displayCriteria || 'What question do you answer to check in?'}</span>
            </div>
            <span className="criteria-edit-icon">✏️</span>
          </div>
        ) : (
          <div className="success-criteria-edit">
            <label className="criteria-edit-label">What counts as a check-in?</label>
            <input
              type="text"
              value={criteriaText}
              onChange={e => setCriteriaText(e.target.value)}
              placeholder={suggestedCriteria || 'e.g. Did I complete this task today?'}
              className="criteria-input"
              maxLength={255}
              autoFocus
            />
            {suggestedCriteria && !criteriaText && (
              <button 
                className="criteria-suggest-btn"
                onClick={() => setCriteriaText(suggestedCriteria)}
              >
                Use suggestion: "{suggestedCriteria}"
              </button>
            )}
            <div className="criteria-edit-actions">
              <button 
                onClick={handleSaveCriteria} 
                disabled={criteriaSaving}
                className="criteria-save-btn"
              >
                {criteriaSaving ? 'Saving...' : 'Save'}
              </button>
              <button onClick={() => setEditingCriteria(false)} className="criteria-cancel-btn">Cancel</button>
            </div>
          </div>
        )}
      </div>
      
      <div className="task-progress">
        <ProgressBar 
          value={task.completions_this_period} 
          max={task.target_per_period}
          color={isComplete ? '#22c55e' : percentage >= 50 ? '#eab308' : '#ef4444'}
        />
        <div className={`task-status ${statusClass}`}>{statusText}</div>
      </div>
      
      <div className="task-details">
        <div className="detail-row">
          <span className="detail-label">Period:</span>
          <span className="detail-value">
            {task.period_start} - {task.extended_deadline && task.extended_deadline > task.period_end 
              ? <><s style={{color:'#64748b'}}>{task.period_end}</s> <span style={{color:'#f59e0b',fontWeight:600}}>{task.extended_deadline}</span></>
              : task.period_end}
          </span>
        </div>
        {task.deadline_pushes_this_period > 0 && (
          <div className="detail-row">
            <span className="detail-label">Extensions:</span>
            <span className="detail-value" style={{color: task.deadline_pushes_this_period >= 3 ? '#ef4444' : '#f59e0b'}}>
              {task.deadline_pushes_this_period}/3 used this period
            </span>
          </div>
        )}
        <div className="detail-row">
          <span className="detail-label">Frequency:</span>
          <span className="detail-value">{task.frequency_type}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Reminder:</span>
          <span className="detail-value">{task.reminder_time}</span>
        </div>
        {task.shields > 0 && (
          <div className="detail-row shields">
            <span className="detail-label">Shields:</span>
            <span className="detail-value">{task.shields}</span>
          </div>
        )}
      </div>

      {/* Punishment Section */}
      {(() => {
        const effectivePunishment = task.punishment_text || defaultPunishment;
        const isFromDefault = !task.punishment_text && !!defaultPunishment;
        const hasPunishment = !!effectivePunishment;
        return (
          <div className="success-criteria-section" style={{marginTop:'0.25rem'}}>
            {!editingPunishment ? (
              <div 
                className={`success-criteria-display ${!hasPunishment ? 'suggested' : ''}`}
                onClick={() => { setEditingPunishment(true); setPunishmentText(task.punishment_text || ''); }}
                title="Click to set/edit task-specific punishment"
                style={hasPunishment && !isComplete ? {borderColor:'#ef444440',background:'#ef444410'} : {}}
              >
                <span className="criteria-icon">{hasPunishment ? '⚡' : '🔨'}</span>
                <div className="criteria-content">
                  <span className="criteria-label">
                    {hasPunishment 
                      ? (isFromDefault ? 'Punishment (default)' : 'Punishment if failed')
                      : 'Set a punishment'}
                  </span>
                  <span className="criteria-text">
                    {effectivePunishment || 'What happens if you don\'t meet your goal?'}
                    {isFromDefault && <span style={{fontSize:'0.65rem',color:'#64748b',marginLeft:'0.25rem'}}>(from default — click to override)</span>}
                  </span>
                </div>
                <span className="criteria-edit-icon">✏️</span>
              </div>
            ) : (
              <div className="success-criteria-edit">
                <label className="criteria-edit-label">What happens if you fail this task?</label>
                <input
                  type="text"
                  value={punishmentText}
                  onChange={e => setPunishmentText(e.target.value)}
                  placeholder={defaultPunishment ? `Default: ${defaultPunishment}` : 'e.g. Donate $20 to charity, no gaming for a day...'}
                  className="criteria-input"
                  maxLength={500}
                  autoFocus
                />
                {defaultPunishment && !punishmentText && (
                  <div style={{fontSize:'0.7rem',color:'#64748b',margin:'0.25rem 0'}}>
                    Leave blank to use default: "{defaultPunishment}"
                  </div>
                )}
                <div className="criteria-edit-actions">
                  <button onClick={handleSavePunishment} disabled={punishmentSaving} className="criteria-save-btn">
                    {punishmentSaving ? 'Saving...' : 'Save'}
                  </button>
                  <button onClick={() => setEditingPunishment(false)} className="criteria-cancel-btn">Cancel</button>
                  {task.punishment_text && (
                    <button onClick={() => { setPunishmentText(''); }} className="criteria-cancel-btn" style={{color:'#ef4444'}}>
                      Remove override
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })()}

      {/* Benefits — Why I do this */}
      <div className="success-criteria-section" style={{marginTop:'0.25rem'}}>
        {!editingBenefits ? (
          <div
            className={`success-criteria-display ${!task.benefits_text ? 'suggested' : ''}`}
            onClick={() => { setEditingBenefits(true); setBenefitsText(task.benefits_text || ''); }}
            title="Click to set/edit — why did you start this?"
            style={task.benefits_text ? {borderColor:'#22c55e40',background:'#22c55e10'} : {}}
          >
            <span className="criteria-icon">{task.benefits_text ? '🌟' : '💡'}</span>
            <div className="criteria-content">
              <span className="criteria-label">
                {task.benefits_text ? 'Why I do this' : 'Why did you start this?'}
              </span>
              <span className="criteria-text">
                {task.benefits_text || 'Remind yourself of the benefits & purpose...'}
              </span>
            </div>
          </div>
        ) : (
          <div className="criteria-edit-section">
            <textarea
              value={benefitsText}
              onChange={e => setBenefitsText(e.target.value)}
              placeholder="e.g. More energy, better health, career growth, confidence..."
              className="criteria-input"
              rows={2}
              maxLength={500}
            />
            <div className="criteria-edit-actions">
              <button
                onClick={() => handleSaveField(
                  'update_benefits', 'benefits_text', benefitsText,
                  () => { task.benefits_text = benefitsText.trim() || null; setEditingBenefits(false); },
                  setBenefitsSaving
                )}
                disabled={benefitsSaving}
                className="criteria-save-btn"
              >{benefitsSaving ? 'Saving...' : 'Save'}</button>
              <button onClick={() => setEditingBenefits(false)} className="criteria-cancel-btn">Cancel</button>
              {task.benefits_text && (
                <button onClick={() => setBenefitsText('')} className="criteria-cancel-btn" style={{color:'#ef4444'}}>Clear</button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Consequences — What happens if I don't */}
      <div className="success-criteria-section" style={{marginTop:'0.25rem'}}>
        {!editingConsequences ? (
          <div
            className={`success-criteria-display ${!task.consequences_text ? 'suggested' : ''}`}
            onClick={() => { setEditingConsequences(true); setConsequencesText(task.consequences_text || ''); }}
            title="Click to set/edit — what happens if you stop?"
            style={task.consequences_text ? {borderColor:'#dc262640',background:'#dc262608'} : {}}
          >
            <span className="criteria-icon">{task.consequences_text ? '⚠️' : '🤔'}</span>
            <div className="criteria-content">
              <span className="criteria-label">
                {task.consequences_text ? 'What happens if I don\'t' : 'What happens if you stop?'}
              </span>
              <span className="criteria-text" style={task.consequences_text ? {color:'#dc2626',fontWeight:500} : {}}>
                {task.consequences_text || 'The real consequences of quitting or neglecting this...'}
              </span>
            </div>
          </div>
        ) : (
          <div className="criteria-edit-section">
            <textarea
              value={consequencesText}
              onChange={e => setConsequencesText(e.target.value)}
              placeholder="e.g. Health declines, lose my progress, regret, let people down..."
              className="criteria-input"
              rows={2}
              maxLength={500}
            />
            <div className="criteria-edit-actions">
              <button
                onClick={() => handleSaveField(
                  'update_consequences', 'consequences_text', consequencesText,
                  () => { task.consequences_text = consequencesText.trim() || null; setEditingConsequences(false); },
                  setConsequencesSaving
                )}
                disabled={consequencesSaving}
                className="criteria-save-btn"
              >{consequencesSaving ? 'Saving...' : 'Save'}</button>
              <button onClick={() => setEditingConsequences(false)} className="criteria-cancel-btn">Cancel</button>
              {task.consequences_text && (
                <button onClick={() => setConsequencesText('')} className="criteria-cancel-btn" style={{color:'#ef4444'}}>Clear</button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Science-backed guidance for gym/fitness tasks */}
      {(() => {
        const tpl = (task.task_template || '').toLowerCase();
        const isFitness = tpl === 'gym' || tpl === 'workout' || tpl === 'stretch' || tpl === 'exercise'
          || (task.custom_name && /gym|workout|fitness|exercise|lift|run|cardio|training/i.test(task.custom_name));
        if (!isFitness) return null;

        const tips = [
          { icon: '⏱️', title: 'Bad day? Just 10 minutes.', text: 'Any exercise > no exercise. Your only job is to not break the chain. Mood improves within 5 min of starting (Health Psychology Review, 2018).' },
          { icon: '📍', title: 'Pre-decide when & where.', text: '"I will go to the gym at [TIME] at [PLACE]." Implementation intentions make you 2-3x more likely to follow through (Gollwitzer, 1999).' },
          { icon: '🎧', title: 'Temptation bundle it.', text: 'Save your favorite podcast/show for gym-only. Gym visits increased 51% in Milkman\'s Wharton study using this technique.' },
          { icon: '🪞', title: 'You\'re an athlete now.', text: '"I am someone who works out" — identity-based habits create less friction than outcome goals. Each check-in is a vote for who you\'re becoming.' },
          { icon: '🏠', title: 'Eliminate friction tonight.', text: 'Set out clothes, pack your bag, put keys on top. People with a closer gym go 2x more — it\'s not willpower, it\'s environment design (Wood, 2019).' },
        ];
        // Pick a tip based on day of year so it rotates daily but is stable within a day
        const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(),0,0).getTime()) / 86400000);
        const tip = tips[dayOfYear % tips.length];

        return (
          <div style={{
            marginTop: '0.35rem',
            padding: '10px 14px',
            background: 'linear-gradient(135deg, rgba(34,197,94,0.06), rgba(59,130,246,0.06))',
            border: '1px solid rgba(34,197,94,0.15)',
            borderRadius: '10px',
            fontSize: '0.82rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
              <span style={{ fontSize: '1.1rem', flexShrink: 0 }}>{tip.icon}</span>
              <div>
                <div style={{ fontWeight: 700, color: '#f1f5f9', marginBottom: '2px' }}>
                  {tip.title}
                </div>
                <div style={{ color: '#94a3b8', lineHeight: 1.45 }}>
                  {tip.text}
                </div>
              </div>
            </div>
            <div style={{ marginTop: '8px', textAlign: 'right' }}>
              <a
                href="/fc/motivation.html"
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: '0.72rem', color: '#3b82f6', textDecoration: 'none', fontWeight: 600 }}
              >
                Read all science-backed tips &rarr;
              </a>
            </div>
          </div>
        );
      })()}
      
      <div className="task-stats">
        <div className="stat"><span className="stat-value">{task.current_streak}</span><span className="stat-label">Current</span></div>
        <div className="stat"><span className="stat-value">{task.longest_streak}</span><span className="stat-label">Best</span></div>
        <div className="stat"><span className="stat-value" style={{ color: tier.color }}>{tier.emoji}</span><span className="stat-label">{task.streak_tier || 'None'}</span></div>
      </div>

      {/* Check-in section with optional note */}
      <div className="checkin-section">
        <div className="checkin-note-row">
          <input
            type="text"
            value={checkinNote}
            onChange={e => setCheckinNote(e.target.value)}
            placeholder="Add a note with your check-in (optional)"
            className="checkin-note-input"
            onKeyDown={e => { if (e.key === 'Enter' && !task.is_paused && !isLoading) handleCheckinClick(); }}
          />
        </div>
        <button 
          className="checkin-button"
          onClick={handleCheckinClick}
          disabled={task.is_paused || isLoading}
        >
          {isLoading ? 'Checking in...' : displayCriteria ? `Yes! ${displayCriteria.replace(/\?$/, '')}` : 'Check In'}
        </button>
      </div>

      {/* Action buttons row */}
      <div className="task-action-row">
        {!isComplete && (
          <button className="task-action-btn" onClick={() => setShowSkipModal(!showSkipModal)} style={{color:'#f59e0b'}}>
            ⏭️ Skip
          </button>
        )}
        <button className="task-action-btn" onClick={() => setShowNoteInput(!showNoteInput)}>
          📝 Note
        </button>
        <button className="task-action-btn" onClick={handleToggleHistory}>
          {showHistory ? '📜 Hide' : '📜 History'}
        </button>
      </div>

      {/* Skip Modal */}
      {showSkipModal && (
        <div className="note-input-section" style={{borderColor:'#f59e0b40'}}>
          <label className="criteria-edit-label" style={{color:'#f59e0b'}}>⏭️ Skip &amp; Extend Deadline</label>
          <div style={{display:'flex',gap:'0.5rem',marginBottom:'0.5rem',flexWrap:'wrap'}}>
            {skipReasonOptions.map(opt => (
              <button
                key={opt.value}
                onClick={() => setSkipReason(opt.value)}
                style={{
                  padding:'0.25rem 0.5rem', borderRadius:'0.375rem', fontSize:'0.75rem', cursor:'pointer',
                  border: skipReason === opt.value ? '2px solid #f59e0b' : '1px solid #334155',
                  background: skipReason === opt.value ? '#f59e0b20' : '#1e293b',
                  color: skipReason === opt.value ? '#f59e0b' : '#94a3b8',
                  fontWeight: skipReason === opt.value ? 600 : 400
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <input
            type="text"
            value={skipNotes}
            onChange={e => setSkipNotes(e.target.value)}
            placeholder="Additional notes (optional)"
            className="criteria-input"
            maxLength={500}
          />
          <div style={{display:'flex',alignItems:'center',gap:'0.75rem',margin:'0.5rem 0'}}>
            <span style={{fontSize:'0.8rem',color:'#94a3b8'}}>Extend deadline by:</span>
            {[0,1,2,3].map(d => (
              <button
                key={d}
                onClick={() => setSkipExtendDays(d)}
                disabled={d > 0 && task.deadline_pushes_this_period >= 3}
                style={{
                  padding:'0.25rem 0.5rem', borderRadius:'0.375rem', fontSize:'0.75rem', cursor:'pointer',
                  border: skipExtendDays === d ? '2px solid #8b5cf6' : '1px solid #334155',
                  background: skipExtendDays === d ? '#8b5cf620' : '#1e293b',
                  color: skipExtendDays === d ? '#8b5cf6' : '#94a3b8',
                  fontWeight: skipExtendDays === d ? 600 : 400,
                  opacity: (d > 0 && task.deadline_pushes_this_period >= 3) ? 0.4 : 1
                }}
              >
                {d === 0 ? 'No extend' : `+${d} day${d>1?'s':''}`}
              </button>
            ))}
          </div>
          {skipReason === 'motivation' && (
            <div style={{
              fontSize:'0.78rem', color:'#94a3b8', margin:'0.5rem 0', padding:'8px 12px',
              background:'rgba(59,130,246,0.08)', border:'1px solid rgba(59,130,246,0.15)', borderRadius:'8px'
            }}>
              <strong style={{color:'#3b82f6'}}>Before you skip:</strong> Research shows mood improves within 5 min of starting. Try the 2-Minute Rule — just put on your shoes. You can always leave after.{' '}
              <a href="/fc/motivation.html" target="_blank" rel="noopener noreferrer" style={{color:'#3b82f6',textDecoration:'underline'}}>Read the science</a>
            </div>
          )}
          {task.deadline_pushes_this_period >= 3 && (
            <div style={{fontSize:'0.75rem',color:'#ef4444',marginBottom:'0.5rem'}}>
              Maximum 3 extensions reached this period. You can still log a skip without extending.
            </div>
          )}
          <div className="note-input-actions">
            <button onClick={() => setShowSkipModal(false)} className="criteria-cancel-btn">Cancel</button>
            <button
              onClick={handleSkipSubmit}
              disabled={skipSubmitting}
              className="note-save-btn"
              style={{background:'#f59e0b',color:'#000'}}
            >
              {skipSubmitting ? 'Submitting...' : 'Log Skip'}
            </button>
          </div>
        </div>
      )}

      {/* Add Note Input */}
      {showNoteInput && (
        <div className="note-input-section">
          <textarea
            value={newNote}
            onChange={e => setNewNote(e.target.value)}
            placeholder="Write a note about this task... (reflections, progress updates, blockers, etc.)"
            className="note-textarea"
            rows={3}
            maxLength={2000}
          />
          <div className="note-input-actions">
            <span className="note-char-count">{newNote.length}/2000</span>
            <button 
              onClick={handleAddNote} 
              disabled={noteSubmitting || !newNote.trim()}
              className="note-save-btn"
            >
              {noteSubmitting ? 'Saving...' : 'Save Note'}
            </button>
          </div>
        </div>
      )}

      {/* Task History Timeline */}
      {showHistory && (
        <div className="task-history-section">
          <h4 className="history-title">Task History</h4>
          {historyLoading ? (
            <div className="history-loading">Loading history...</div>
          ) : history.length === 0 ? (
            <div className="history-empty">No history yet. Check in or add a note to get started!</div>
          ) : (
            <div className="history-timeline">
              {history.map((item, idx) => {
                const date = new Date(item.created_at);
                const dateStr = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
                const timeStr = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
                return (
                  <div key={`${item.type}-${item.id}-${idx}`} className={`history-item history-${item.type}`}>
                    <div className="history-dot-col">
                      <div className={`history-dot ${item.type === 'checkin' ? 'dot-checkin' : 'dot-note'}`}>
                        {item.type === 'checkin' ? '✅' : '📝'}
                      </div>
                      {idx < history.length - 1 && <div className="history-line" />}
                    </div>
                    <div className="history-content">
                      <div className="history-meta">
                        <span className="history-type-label">
                          {item.type === 'checkin' ? 'Check-in' : 'Note'}
                        </span>
                        <span className="history-timestamp">{dateStr} at {timeStr}</span>
                      </div>
                      {item.text && <div className="history-text">{item.text}</div>}
                      {item.type === 'checkin' && !item.text && (
                        <div className="history-text history-text-default">Checked in successfully</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Identity card component
function IdentityCard({ identity }: { identity: Identity }) {
  const barWidth = Math.min(identity.adherence, 100);
  const statusColors = { strong: '#22c55e', moderate: '#eab308', needs_attention: '#ef4444' };
  
  return (
    <div className={`identity-card ${identity.status}`}>
      <div className="identity-header">
        <span className="identity-emoji">{identity.emoji}</span>
        <span className="identity-name">{identity.name}</span>
        <span className="identity-percentage">{identity.adherence}%</span>
      </div>
      <div className="identity-bar">
        <div className="identity-bar-fill" style={{ width: `${barWidth}%`, backgroundColor: statusColors[identity.status] }} />
      </div>
      {identity.status === 'needs_attention' && <div className="identity-warning">Needs attention</div>}
    </div>
  );
}

// Recent activity component with full timestamps
function RecentActivity({ checkins }: { checkins: Checkin[] }) {
  if (checkins.length === 0) {
    return <div className="recent-activity empty"><p>No recent check-ins yet. Start logging your habits!</p></div>;
  }
  
  return (
    <div className="recent-activity">
      {checkins.slice(0, 20).map((checkin) => {
        const date = new Date(checkin.checkin_time);
        const timeAgo = getTimeAgo(date);
        const dateStr = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        const timeStr = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
        return (
          <div key={checkin.id} className="activity-item">
            <div className="activity-icon">✅</div>
            <div className="activity-content">
              <div className="activity-task">{checkin.task_name}</div>
              {checkin.notes && <div className="activity-notes">{checkin.notes}</div>}
              <div className="activity-date-detail">{dateStr} at {timeStr}</div>
            </div>
            <div className="activity-time">{timeAgo}</div>
          </div>
        );
      })}
    </div>
  );
}

// Pattern insight component
function PatternInsight({ pattern }: { pattern: Pattern }) {
  const typeIcons: Record<string, string> = { best_day: '📅', worst_day: '⚠️', best_time: '⏰', worst_time: '🚫', skip_reason_trend: '📊', success_rate: '📈' };
  return (
    <div className="pattern-card">
      <span className="pattern-icon">{typeIcons[pattern.type] || '💡'}</span>
      <span className="pattern-insight">{pattern.insight}</span>
      <span className="pattern-confidence">{Math.round(pattern.confidence * 100)}% confident</span>
    </div>
  );
}

// Stats overview component
function StatsOverview({ stats }: { stats: DashboardData['stats'] }) {
  return (
    <div className="stats-overview">
      <div className="stat-card"><div className="stat-icon">✅</div><div className="stat-number">{stats.total_checkins}</div><div className="stat-label">Total Check-ins</div></div>
      <div className="stat-card"><div className="stat-icon">🎯</div><div className="stat-number">{stats.active_tasks}</div><div className="stat-label">Active Tasks</div></div>
      <div className="stat-card on-track"><div className="stat-icon">🟢</div><div className="stat-number">{stats.on_track}</div><div className="stat-label">On Track</div></div>
      <div className="stat-card behind"><div className="stat-icon">🔴</div><div className="stat-number">{stats.behind}</div><div className="stat-label">Behind</div></div>
      <div className="stat-card"><div className="stat-icon">🛡️</div><div className="stat-number">{stats.total_shields}</div><div className="stat-label">Shields</div></div>
      <div className="stat-card"><div className="stat-icon">🔥</div><div className="stat-number">{stats.highest_streak}</div><div className="stat-label">Best Streak</div></div>
    </div>
  );
}

// Toast notification component
function ToastContainer({ toasts, onDismiss }: { toasts: ToastItem[]; onDismiss: (id: string) => void }) {
  if (toasts.length === 0) return null;
  
  const typeColors: Record<string, string> = {
    info: '#3b82f6',
    warning: '#f59e0b',
    success: '#22c55e',
    celebration: '#a855f7',
  };
  const typeIcons: Record<string, string> = {
    info: '🔔',
    warning: '⚠️',
    success: '✅',
    celebration: '🎉',
  };
  
  return (
    <div style={{
      position: 'fixed', top: '1rem', right: '1rem', zIndex: 10000,
      display: 'flex', flexDirection: 'column', gap: '0.5rem', maxWidth: '360px'
    }}>
      {toasts.map((toast) => (
        <div key={toast.id} style={{
          background: '#1e293b', border: `1px solid ${typeColors[toast.type] || '#3b82f6'}40`,
          borderLeft: `4px solid ${typeColors[toast.type] || '#3b82f6'}`,
          borderRadius: '0.75rem', padding: '0.75rem 1rem', color: '#f8fafc',
          boxShadow: '0 10px 25px rgba(0,0,0,0.5)', animation: 'slideIn 0.3s ease-out',
          display: 'flex', gap: '0.5rem', alignItems: 'flex-start'
        }}>
          <span style={{ fontSize: '1.25rem', flexShrink: 0 }}>{typeIcons[toast.type] || '🔔'}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.15rem' }}>{toast.title}</div>
            {toast.body && <div style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.4 }}>{toast.body}</div>}
          </div>
          <button
            onClick={() => onDismiss(toast.id)}
            style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '1rem', padding: '0', lineHeight: 1 }}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

// Task Setup Form component
function TaskSetupForm({ appUserId, onTaskCreated }: { appUserId: number; onTaskCreated: () => void }) {
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [customName, setCustomName] = useState('');
  const [successCriteria, setSuccessCriteria] = useState('');
  const [frequency, setFrequency] = useState('daily');
  const [target, setTarget] = useState(1);
  const [reminderTime, setReminderTime] = useState('09:00');
  const [submitting, setSubmitting] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [setupSuccess, setSetupSuccess] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<string | null>(null);

  // When template is selected, set its defaults
  const handleSelectTemplate = (key: string) => {
    setSelectedTemplate(key);
    setSetupError(null);
    setSetupSuccess(null);
    const tpl = TEMPLATE_NAMES[key];
    if (tpl) {
      // Set reasonable defaults based on template
      const defaults: Record<string, { freq: string; target: number }> = {
        gym: { freq: 'every2days', target: 1 },
        water: { freq: 'daily', target: 8 },
        meals: { freq: 'daily', target: 3 },
        cleaning: { freq: 'weekly', target: 1 },
      };
      const d = defaults[key] || { freq: 'daily', target: 1 };
      setFrequency(d.freq);
      setTarget(d.target);
    }
    // Pre-fill suggested success criteria
    setSuccessCriteria(DEFAULT_SUCCESS_CRITERIA[key] || '');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTemplate) return;

    setSubmitting(true);
    setSetupError(null);
    setSetupSuccess(null);

    try {
      const response = await fetch(`${getApiBase()}/accountability/web_setup.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_user_id: appUserId,
          taskname: selectedTemplate,
          custom_name: selectedTemplate === 'custom' ? customName : undefined,
          success_criteria: successCriteria || undefined,
          frequency,
          target,
          reminder_time: reminderTime,
        }),
      });

      const result = await response.json();

      if (result.error) {
        setSetupError(result.error);
      } else if (result.success) {
        setSetupSuccess(`"${result.task.display_name}" created! ${result.onboarding.schedule}`);
        // Reset form
        setSelectedTemplate(null);
        setCustomName('');
        setSuccessCriteria('');
        // Refresh dashboard
        setTimeout(() => onTaskCreated(), 1500);
      }
    } catch (err) {
      setSetupError(err instanceof Error ? err.message : 'Failed to create task');
    } finally {
      setSubmitting(false);
    }
  };

  // Group templates by category
  const categories = Object.keys(CATEGORY_LABELS);
  const templatesByCategory: Record<string, Array<{ key: string; name: string; emoji: string }>> = {};
  categories.forEach(cat => { templatesByCategory[cat] = []; });
  Object.entries(TEMPLATE_NAMES).forEach(([key, val]) => {
    if (templatesByCategory[val.category]) {
      templatesByCategory[val.category].push({ key, name: val.name, emoji: val.emoji });
    }
  });

  const filteredCategories = filterCategory
    ? categories.filter(c => c === filterCategory)
    : categories;

  return (
    <div className="setup-form-container">
      <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem', color: '#f8fafc' }}>
        Add a New Task
      </h2>
      <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: '1rem' }}>
        Pick a habit template or create a custom one.
      </p>

      {setupSuccess && (
        <div style={{ background: '#22c55e20', border: '1px solid #22c55e40', borderRadius: '0.5rem', padding: '0.75rem 1rem', color: '#4ade80', marginBottom: '1rem', fontSize: '0.85rem' }}>
          ✅ {setupSuccess}
        </div>
      )}
      {setupError && (
        <div style={{ background: '#ef444420', border: '1px solid #ef444440', borderRadius: '0.5rem', padding: '0.75rem 1rem', color: '#f87171', marginBottom: '1rem', fontSize: '0.85rem' }}>
          {setupError}
        </div>
      )}

      {/* Category filter pills */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <button
          onClick={() => setFilterCategory(null)}
          style={{
            padding: '0.35rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 600,
            background: !filterCategory ? '#8b5cf620' : 'transparent',
            border: `1px solid ${!filterCategory ? '#8b5cf6' : '#ffffff15'}`,
            color: !filterCategory ? '#c4b5fd' : '#94a3b8', cursor: 'pointer'
          }}
        >
          All
        </button>
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setFilterCategory(filterCategory === cat ? null : cat)}
            style={{
              padding: '0.35rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 600,
              background: filterCategory === cat ? '#8b5cf620' : 'transparent',
              border: `1px solid ${filterCategory === cat ? '#8b5cf6' : '#ffffff15'}`,
              color: filterCategory === cat ? '#c4b5fd' : '#94a3b8', cursor: 'pointer'
            }}
          >
            {CATEGORY_LABELS[cat].emoji} {CATEGORY_LABELS[cat].label}
          </button>
        ))}
      </div>

      {/* Template grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '0.5rem', marginBottom: '1rem' }}>
        {filteredCategories.map(cat =>
          templatesByCategory[cat].map(tpl => (
            <button
              key={tpl.key}
              onClick={() => handleSelectTemplate(tpl.key)}
              style={{
                padding: '0.75rem 0.5rem', borderRadius: '0.75rem', cursor: 'pointer',
                background: selectedTemplate === tpl.key ? '#8b5cf630' : '#ffffff08',
                border: `1px solid ${selectedTemplate === tpl.key ? '#8b5cf6' : '#ffffff10'}`,
                color: selectedTemplate === tpl.key ? '#c4b5fd' : '#e2e8f0',
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.25rem',
                transition: 'all 0.2s'
              }}
            >
              <span style={{ fontSize: '1.5rem' }}>{tpl.emoji}</span>
              <span style={{ fontSize: '0.7rem', fontWeight: 600, textAlign: 'center', lineHeight: 1.2 }}>{tpl.name}</span>
            </button>
          ))
        )}
        {/* Custom option */}
        <button
          onClick={() => handleSelectTemplate('custom')}
          style={{
            padding: '0.75rem 0.5rem', borderRadius: '0.75rem', cursor: 'pointer',
            background: selectedTemplate === 'custom' ? '#8b5cf630' : '#ffffff08',
            border: `1px solid ${selectedTemplate === 'custom' ? '#8b5cf6' : '#ffffff10'}`,
            color: selectedTemplate === 'custom' ? '#c4b5fd' : '#e2e8f0',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.25rem',
            transition: 'all 0.2s'
          }}
        >
          <span style={{ fontSize: '1.5rem' }}>✨</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 600, textAlign: 'center' }}>Custom</span>
        </button>
      </div>

      {/* Setup form (shows when template selected) */}
      {selectedTemplate && (
        <form onSubmit={handleSubmit} style={{
          background: '#0f172a', border: '1px solid #ffffff15', borderRadius: '0.75rem', padding: '1rem', marginTop: '0.5rem'
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            {selectedTemplate === 'custom' && (
              <div style={{ gridColumn: '1 / -1' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.25rem' }}>Task Name</label>
                <input
                  type="text"
                  value={customName}
                  onChange={e => setCustomName(e.target.value)}
                  placeholder="e.g. Practice guitar"
                  required
                  style={{
                    width: '100%', padding: '0.5rem 0.75rem', borderRadius: '0.5rem', fontSize: '0.85rem',
                    background: '#1e293b', border: '1px solid #ffffff15', color: '#f8fafc', outline: 'none'
                  }}
                />
              </div>
            )}
            {/* Success Criteria */}
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.25rem' }}>
                🎯 Success Criteria <span style={{ fontWeight: 400, color: '#64748b' }}>(What question do you answer to check in?)</span>
              </label>
              <input
                type="text"
                value={successCriteria}
                onChange={e => setSuccessCriteria(e.target.value)}
                placeholder={DEFAULT_SUCCESS_CRITERIA[selectedTemplate] || 'e.g. Did I complete this task today?'}
                maxLength={255}
                style={{
                  width: '100%', padding: '0.5rem 0.75rem', borderRadius: '0.5rem', fontSize: '0.85rem',
                  background: '#1e293b', border: '1px solid #ffffff15', color: '#f8fafc', outline: 'none'
                }}
              />
              <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.25rem' }}>
                This defines what "done" looks like. Example: "Did I show up at the gym?" or "I did my daily swipes for the day"
              </div>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.25rem' }}>Frequency</label>
              <select
                value={frequency}
                onChange={e => setFrequency(e.target.value)}
                style={{
                  width: '100%', padding: '0.5rem 0.75rem', borderRadius: '0.5rem', fontSize: '0.85rem',
                  background: '#1e293b', border: '1px solid #ffffff15', color: '#f8fafc', outline: 'none'
                }}
              >
                {FREQUENCY_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.25rem' }}>Target per Period</label>
              <input
                type="number"
                min={1}
                max={50}
                value={target}
                onChange={e => setTarget(parseInt(e.target.value) || 1)}
                style={{
                  width: '100%', padding: '0.5rem 0.75rem', borderRadius: '0.5rem', fontSize: '0.85rem',
                  background: '#1e293b', border: '1px solid #ffffff15', color: '#f8fafc', outline: 'none'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.25rem' }}>Reminder Time</label>
              <input
                type="time"
                value={reminderTime}
                onChange={e => setReminderTime(e.target.value)}
                style={{
                  width: '100%', padding: '0.5rem 0.75rem', borderRadius: '0.5rem', fontSize: '0.85rem',
                  background: '#1e293b', border: '1px solid #ffffff15', color: '#f8fafc', outline: 'none'
                }}
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={submitting || (selectedTemplate === 'custom' && !customName)}
            style={{
              width: '100%', marginTop: '0.75rem', padding: '0.65rem',
              borderRadius: '0.5rem', fontWeight: 700, fontSize: '0.9rem',
              background: '#8b5cf6', color: 'white', border: 'none', cursor: 'pointer',
              opacity: submitting ? 0.6 : 1
            }}
          >
            {submitting ? 'Creating...' : 'Create Task'}
          </button>
        </form>
      )}
    </div>
  );
}

// Browser notification permission prompt
function NotificationPermissionBanner({ onGrant }: { onGrant: () => void }) {
  const [dismissed, setDismissed] = useState(false);
  
  if (dismissed) return null;
  if (typeof Notification === 'undefined') return null;
  if (Notification.permission === 'granted') return null;
  if (Notification.permission === 'denied') return null;

  const handleEnable = async () => {
    const perm = await Notification.requestPermission();
    if (perm === 'granted') {
      onGrant();
    }
    setDismissed(true);
  };

  return (
    <div style={{
      background: '#1e293b', border: '1px solid #8b5cf640', borderRadius: '0.75rem',
      padding: '0.75rem 1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem'
    }}>
      <span style={{ fontSize: '1.5rem' }}>🔔</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#f8fafc' }}>Enable Browser Notifications</div>
        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
          Get reminders even when this tab isn't focused. We'll only notify you about your accountability tasks.
        </div>
      </div>
      <button
        onClick={handleEnable}
        style={{
          padding: '0.4rem 0.75rem', borderRadius: '0.5rem', fontSize: '0.75rem', fontWeight: 600,
          background: '#8b5cf6', color: 'white', border: 'none', cursor: 'pointer', whiteSpace: 'nowrap'
        }}
      >
        Enable
      </button>
      <button
        onClick={() => setDismissed(true)}
        style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '1rem' }}
      >
        ×
      </button>
    </div>
  );
}

// Helper function
function getTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  if (diffMins > 0) return `${diffMins}m ago`;
  return 'Just now';
}

// Main Dashboard Component
// Default punishment banner/editor
function DefaultPunishmentBanner({ value, discordId, appUserId, addToast, onSaved }: {
  value: string | null;
  discordId: string;
  appUserId: number | null;
  addToast: (title: string, body: string, type?: 'info' | 'warning' | 'success' | 'celebration') => void;
  onSaved: (val: string | null) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(value || '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const body: Record<string, unknown> = {
        action: 'set_default_punishment',
        default_punishment: text.trim() || null,
      };
      if (appUserId) body.app_user_id = appUserId;
      if (discordId) body.discord_id = discordId;

      const res = await fetch(`${getApiBase()}/accountability/dashboard.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = await res.json();
      if (result.success) {
        onSaved(text.trim() || null);
        setEditing(false);
        addToast('Updated!', text.trim() ? 'Default punishment saved for all tasks.' : 'Default punishment removed.', 'success');
      } else {
        addToast('Error', result.error || 'Failed to save', 'warning');
      }
    } catch {
      addToast('Error', 'Failed to save default punishment', 'warning');
    } finally {
      setSaving(false);
    }
  };

  if (!editing) {
    return (
      <div 
        onClick={() => { setEditing(true); setText(value || ''); }}
        style={{
          margin: '0 1rem 0.75rem', padding: '0.6rem 0.85rem', borderRadius: '0.75rem', cursor: 'pointer',
          background: value ? '#ef444410' : '#1e293b',
          border: value ? '1px solid #ef444430' : '1px dashed #334155',
          display: 'flex', alignItems: 'center', gap: '0.5rem',
          transition: 'border-color 0.2s'
        }}
      >
        <span style={{fontSize:'1.1rem'}}>{value ? '⚡' : '🔨'}</span>
        <div style={{flex:1,minWidth:0}}>
          <div style={{fontSize:'0.7rem',fontWeight:600,color: value ? '#f87171' : '#64748b',textTransform:'uppercase',letterSpacing:'0.05em'}}>
            {value ? 'Default Punishment (all tasks)' : 'Set a default punishment for all tasks'}
          </div>
          {value && <div style={{fontSize:'0.8rem',color:'#e2e8f0',marginTop:'0.1rem'}}>{value}</div>}
        </div>
        <span style={{color:'#64748b',fontSize:'0.8rem'}}>✏️</span>
      </div>
    );
  }

  return (
    <div style={{
      margin: '0 1rem 0.75rem', padding: '0.75rem', borderRadius: '0.75rem',
      background: '#0f172a', border: '1px solid #334155'
    }}>
      <label style={{fontSize:'0.75rem',fontWeight:600,color:'#f87171',display:'block',marginBottom:'0.35rem'}}>
        ⚡ Default Punishment (applies to all tasks without a specific one)
      </label>
      <input
        type="text"
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="e.g. Donate $20 to charity, no gaming for a day..."
        maxLength={500}
        autoFocus
        style={{
          width:'100%',padding:'0.5rem',borderRadius:'0.5rem',border:'1px solid #334155',
          background:'#1e293b',color:'#f8fafc',fontSize:'0.8rem',boxSizing:'border-box'
        }}
      />
      <div style={{display:'flex',gap:'0.5rem',marginTop:'0.5rem',justifyContent:'flex-end'}}>
        <button onClick={() => setEditing(false)} style={{
          padding:'0.3rem 0.6rem',borderRadius:'0.375rem',border:'1px solid #334155',
          background:'transparent',color:'#94a3b8',fontSize:'0.75rem',cursor:'pointer'
        }}>Cancel</button>
        {value && (
          <button onClick={() => { setText(''); }} style={{
            padding:'0.3rem 0.6rem',borderRadius:'0.375rem',border:'1px solid #ef444440',
            background:'transparent',color:'#ef4444',fontSize:'0.75rem',cursor:'pointer'
          }}>Remove</button>
        )}
        <button onClick={handleSave} disabled={saving} style={{
          padding:'0.3rem 0.75rem',borderRadius:'0.375rem',border:'none',
          background:'#ef4444',color:'white',fontSize:'0.75rem',cursor:'pointer',fontWeight:600,
          opacity: saving ? 0.7 : 1
        }}>{saving ? 'Saving...' : 'Save Default'}</button>
      </div>
    </div>
  );
}

// Score display component
function ScorePanel({ discordId, appUserId }: { discordId: string; appUserId: number | null }) {
  const [scores, setScores] = useState<Record<string, ScoreData> | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState<string>('month');

  useEffect(() => {
    const fetchScores = async () => {
      try {
        let url = `${getApiBase()}/accountability/score.php?`;
        if (appUserId) url += `app_user_id=${appUserId}`;
        if (discordId) url += `${appUserId ? '&' : ''}discord_id=${discordId}`;
        const res = await fetch(url);
        const data: ScoreResponse = await res.json();
        if (data.success && data.scores) setScores(data.scores);
      } catch { /* silent */ }
      finally { setLoading(false); }
    };
    fetchScores();
  }, [discordId, appUserId]);

  if (loading) return <div style={{textAlign:'center',padding:'2rem',color:'#94a3b8'}}>Calculating your score...</div>;
  if (!scores) return <div style={{textAlign:'center',padding:'2rem',color:'#94a3b8'}}>Not enough data for scoring yet.</div>;

  const gradeColors: Record<string, string> = { S: '#ffd700', A: '#22c55e', B: '#3b82f6', C: '#eab308', D: '#f97316', F: '#ef4444' };
  const gradeEmojis: Record<string, string> = { S: '👑', A: '🌟', B: '✅', C: '🟡', D: '⚠️', F: '🔴' };
  const periodLabels: Record<string, string> = { week: 'This Week', month: 'This Month', year: 'This Year', all: 'All Time' };

  const current = scores[selectedPeriod];
  if (!current) return null;

  return (
    <div>
      {/* Period tabs */}
      <div style={{display:'flex',gap:'0.5rem',marginBottom:'1rem',flexWrap:'wrap'}}>
        {Object.entries(periodLabels).map(([key, label]) => {
          const s = scores[key];
          const active = key === selectedPeriod;
          return (
            <button
              key={key}
              onClick={() => setSelectedPeriod(key)}
              style={{
                padding:'0.5rem 0.75rem', borderRadius:'0.5rem', cursor:'pointer', fontSize:'0.8rem',
                border: active ? `2px solid ${gradeColors[s?.grade||'C']}` : '1px solid #334155',
                background: active ? `${gradeColors[s?.grade||'C']}15` : '#1e293b',
                color: active ? gradeColors[s?.grade||'C'] : '#94a3b8',
                fontWeight: active ? 700 : 400,
                display:'flex', flexDirection:'column', alignItems:'center', gap:'0.15rem', minWidth:'80px'
              }}
            >
              <span style={{fontSize:'1.1rem'}}>{gradeEmojis[s?.grade||'C']}</span>
              <span>{s?.score ?? 0}</span>
              <span style={{fontSize:'0.65rem',opacity:0.7}}>{label}</span>
            </button>
          );
        })}
      </div>

      {/* Big score display */}
      <div style={{textAlign:'center',marginBottom:'1.5rem'}}>
        <div style={{fontSize:'3.5rem',fontWeight:800,color:gradeColors[current.grade]||'#94a3b8',lineHeight:1}}>
          {current.score}
        </div>
        <div style={{fontSize:'1.5rem',color:gradeColors[current.grade]||'#94a3b8',fontWeight:700}}>
          {gradeEmojis[current.grade]} Grade: {current.grade}
        </div>
      </div>

      {/* Breakdown bars */}
      <div style={{marginBottom:'1.5rem'}}>
        <h3 style={{fontSize:'0.9rem',fontWeight:600,color:'#f8fafc',marginBottom:'0.75rem'}}>Score Breakdown</h3>
        {current.breakdown.map((item) => {
          const barColor = item.score >= 80 ? '#22c55e' : item.score >= 60 ? '#eab308' : item.score >= 40 ? '#f97316' : '#ef4444';
          return (
            <div key={item.category} style={{marginBottom:'0.5rem'}}>
              <div style={{display:'flex',justifyContent:'space-between',fontSize:'0.75rem',marginBottom:'0.2rem'}}>
                <span style={{color:'#e2e8f0'}}>{item.category} <span style={{color:'#64748b'}}>({item.weight})</span></span>
                <span style={{color:barColor,fontWeight:600}}>{item.score}%</span>
              </div>
              <div style={{height:'8px',background:'#1e293b',borderRadius:'4px',overflow:'hidden'}}>
                <div style={{width:`${item.score}%`,height:'100%',background:barColor,borderRadius:'4px',transition:'width 0.5s ease'}} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Explanations */}
      {current.explanations.length > 0 && (
        <div style={{marginBottom:'1.25rem',background:'#1e293b',borderRadius:'0.75rem',padding:'1rem',border:'1px solid #334155'}}>
          <h3 style={{fontSize:'0.85rem',fontWeight:600,color:'#94a3b8',marginBottom:'0.5rem'}}>💡 Why this score</h3>
          {current.explanations.map((exp, i) => (
            <p key={i} style={{fontSize:'0.8rem',color:'#e2e8f0',lineHeight:1.5,margin:'0.25rem 0'}}>• {exp}</p>
          ))}
        </div>
      )}

      {/* Tips */}
      {current.tips.length > 0 && (
        <div style={{background:'#1e293b',borderRadius:'0.75rem',padding:'1rem',border:'1px solid #8b5cf640'}}>
          <h3 style={{fontSize:'0.85rem',fontWeight:600,color:'#c4b5fd',marginBottom:'0.5rem'}}>🎯 How to improve</h3>
          {current.tips.map((tip, i) => (
            <p key={i} style={{fontSize:'0.8rem',color:'#e2e8f0',lineHeight:1.5,margin:'0.25rem 0'}}>• {tip}</p>
          ))}
        </div>
      )}

      {/* Stats footer */}
      {current.stats && (
        <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:'0.5rem',marginTop:'1rem'}}>
          {[
            {label:'Check-ins',val:current.stats.total_checkins,icon:'✅'},
            {label:'Active Days',val:current.stats.active_days,icon:'📅'},
            {label:'Skips',val:current.stats.skips,icon:'⏭️'},
            {label:'Extensions',val:current.stats.deadline_pushes,icon:'🔄'},
            {label:'Best Streak',val:current.stats.best_streak,icon:'🔥'},
            {label:'Tasks',val:current.stats.tasks_count,icon:'🎯'},
          ].map(s => (
            <div key={s.label} style={{background:'#0f172a',borderRadius:'0.5rem',padding:'0.5rem',textAlign:'center',border:'1px solid #1e293b'}}>
              <div style={{fontSize:'0.7rem',color:'#64748b'}}>{s.icon} {s.label}</div>
              <div style={{fontSize:'1rem',fontWeight:700,color:'#f8fafc'}}>{s.val}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// PATTERN FINDER — detect correlations between tasks
// ═══════════════════════════════════════════════════════════════════════════

function getPatternConfidenceColor(conf: number): string {
  if (conf >= 70) return '#22c55e';
  if (conf >= 45) return '#eab308';
  return '#f97316';
}

function lagLabel(lag: number): string {
  if (lag === 0) return 'same day';
  if (lag === 1) return 'next day';
  return `${lag} days later`;
}

function formatPatternDate(d: string): string {
  try {
    const dt = new Date(d + 'T12:00:00');
    return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch { return d; }
}

// Individual pattern card
function PatternCard({
  pattern, tasks, onRate, onDismiss
}: {
  pattern: DetectedPattern;
  tasks: Task[];
  onRate: (patternId: number, rating: 'helpful' | 'not_helpful' | null) => void;
  onDismiss: (patternId: number) => void;
}) {
  const [showDetails, setShowDetails] = useState(false);

  const actTask = tasks.find(t => t.id === pattern.activity_task_id);
  const outTask = tasks.find(t => t.id === pattern.outcome_task_id);
  const actDisplay = actTask ? getTaskDisplay(actTask) : { name: pattern.activity_name, emoji: '✨' };
  const outDisplay = outTask ? getTaskDisplay(outTask) : { name: pattern.outcome_name, emoji: '✨' };

  const confColor = getPatternConfidenceColor(pattern.confidence);
  const confPct = Math.min(pattern.confidence, 100);

  return (
    <div className={`pf-card ${pattern.status === 'dismissed' ? 'pf-dismissed' : ''} ${pattern.is_hypothesis ? 'pf-hypothesis' : ''}`}>
      {pattern.is_hypothesis && <span className="pf-hypothesis-badge">Hypothesis</span>}
      {pattern.status === 'dismissed' && <span className="pf-dismissed-badge">Dismissed</span>}

      {/* Header: Activity → Outcome */}
      <div className="pf-card-header">
        <div className="pf-flow">
          <span className="pf-flow-emoji">{actDisplay.emoji}</span>
          <span className="pf-flow-name">{actDisplay.name}</span>
          <span className="pf-flow-arrow">→</span>
          <span className="pf-flow-emoji">{outDisplay.emoji}</span>
          <span className="pf-flow-name">{outDisplay.name}</span>
        </div>
        <span className="pf-lag-badge">{lagLabel(pattern.lag_days)}</span>
      </div>

      {/* Confidence bar */}
      <div className="pf-confidence-row">
        <div className="pf-conf-bar-bg">
          <div className="pf-conf-bar-fill" style={{ width: `${confPct}%`, backgroundColor: confColor }} />
        </div>
        <span className="pf-conf-value" style={{ color: confColor }}>{pattern.confidence}%</span>
      </div>

      {/* Summary */}
      <p className="pf-summary">{pattern.summary}</p>

      {/* Stats row */}
      <div className="pf-stats-row">
        <span title="Times pattern occurred">✅ {pattern.occurrence_count} matches</span>
        <span title="Times pattern did not occur">❌ {pattern.exception_count} exceptions</span>
        <span title="How much more likely than random">{pattern.lift}x lift</span>
      </div>

      {/* Expandable details */}
      <button className="pf-details-toggle" onClick={() => setShowDetails(!showDetails)}>
        {showDetails ? '▾ Hide details' : '▸ View examples & counterexamples'}
      </button>

      {showDetails && (
        <div className="pf-details">
          {pattern.examples && pattern.examples.length > 0 && (
            <div className="pf-examples-section">
              <div className="pf-examples-label">Pattern matched:</div>
              {pattern.examples.map((ex, i) => (
                <div key={i} className="pf-example-row pf-example-positive">
                  <span>✅</span>
                  <span>{formatPatternDate(ex.activity_date)}: {actDisplay.name} done → {formatPatternDate(ex.outcome_date)}: {outDisplay.name} done</span>
                </div>
              ))}
            </div>
          )}
          {pattern.exceptions && pattern.exceptions.length > 0 && (
            <div className="pf-examples-section">
              <div className="pf-examples-label">Exceptions (pattern didn't hold):</div>
              {pattern.exceptions.map((ex, i) => (
                <div key={i} className="pf-example-row pf-example-negative">
                  <span>❌</span>
                  <span>{formatPatternDate(ex.activity_date)}: {actDisplay.name} done → {formatPatternDate(ex.outcome_date)}: {outDisplay.name} missed</span>
                </div>
              ))}
            </div>
          )}
          <div className="pf-detail-stats">
            <span>Base rate: {pattern.base_rate_pct}% (how often outcome happens regardless)</span>
            <span>Consistency: {pattern.consistency_pct}% of the time after the activity</span>
          </div>
        </div>
      )}

      {/* Actions: rate & dismiss */}
      <div className="pf-actions-row">
        <button
          className={`pf-rate-btn ${pattern.user_rating === 'helpful' ? 'pf-rated' : ''}`}
          onClick={() => onRate(pattern.id, pattern.user_rating === 'helpful' ? null : 'helpful')}
          title="Mark as helpful"
        >
          👍 {pattern.user_rating === 'helpful' ? 'Helpful' : ''}
        </button>
        <button
          className={`pf-rate-btn ${pattern.user_rating === 'not_helpful' ? 'pf-rated' : ''}`}
          onClick={() => onRate(pattern.id, pattern.user_rating === 'not_helpful' ? null : 'not_helpful')}
          title="Mark as not helpful"
        >
          👎 {pattern.user_rating === 'not_helpful' ? 'Not helpful' : ''}
        </button>
        {pattern.status !== 'dismissed' && (
          <button className="pf-dismiss-btn" onClick={() => onDismiss(pattern.id)} title="Dismiss this pattern">
            ✕
          </button>
        )}
      </div>
    </div>
  );
}

// Hypothesis creation form (inline)
function HypothesisForm({
  tasks, discordId, appUserId, onCreated
}: {
  tasks: Task[];
  discordId: string;
  appUserId: number | null;
  onCreated: (patterns: DetectedPattern[]) => void;
}) {
  const [activityId, setActivityId] = useState(0);
  const [outcomeId, setOutcomeId] = useState(0);
  const [lag, setLag] = useState(1);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const activeTasks = tasks.filter(t => !t.is_paused);

  const handleCreate = async () => {
    if (!activityId || !outcomeId || activityId === outcomeId) return;
    setSaving(true);
    setError('');
    try {
      const body: Record<string, unknown> = {
        action: 'hypothesis',
        activity_task_id: activityId,
        outcome_task_id: outcomeId,
        lag_days: lag,
      };
      if (appUserId) body.app_user_id = appUserId;
      if (discordId) body.discord_id = discordId;

      const resp = await fetch(`${getApiBase()}/accountability/patterns.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = await resp.json();
      if (result.error) throw new Error(result.error);
      if (result.patterns) onCreated(result.patterns);
      setActivityId(0);
      setOutcomeId(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create hypothesis');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="pf-hypothesis-form">
      <h4>Test Your Own Hypothesis</h4>
      <p className="pf-hypothesis-desc">Think two of your habits are connected? Pick them and we'll check the data.</p>
      <div className="pf-hypothesis-fields">
        <div className="pf-hypothesis-field">
          <label>When I do...</label>
          <select value={activityId} onChange={e => setActivityId(parseInt(e.target.value))}>
            <option value={0}>Select activity</option>
            {activeTasks.map(t => {
              const d = getTaskDisplay(t);
              return <option key={t.id} value={t.id}>{d.emoji} {d.name}</option>;
            })}
          </select>
        </div>
        <div className="pf-hypothesis-field">
          <label>I also tend to...</label>
          <select value={outcomeId} onChange={e => setOutcomeId(parseInt(e.target.value))}>
            <option value={0}>Select outcome</option>
            {activeTasks.filter(t => t.id !== activityId).map(t => {
              const d = getTaskDisplay(t);
              return <option key={t.id} value={t.id}>{d.emoji} {d.name}</option>;
            })}
          </select>
        </div>
        <div className="pf-hypothesis-field">
          <label>Time gap</label>
          <select value={lag} onChange={e => setLag(parseInt(e.target.value))}>
            <option value={0}>Same day</option>
            <option value={1}>Next day</option>
            <option value={2}>2 days later</option>
          </select>
        </div>
        <button
          className="pf-hypothesis-btn"
          onClick={handleCreate}
          disabled={saving || !activityId || !outcomeId || activityId === outcomeId}
        >
          {saving ? 'Checking...' : 'Test It'}
        </button>
      </div>
      {error && <p className="pf-hypothesis-error">{error}</p>}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// SUPER GOALS — probability calculation and components
// ═══════════════════════════════════════════════════════════════════════════

const SUPER_GOAL_ICONS = ['🎯', '🏆', '🌟', '🚀', '💪', '🔥', '💎', '🎪', '⭐', '🏅'];

function calculateSuperGoalProbability(superGoal: SuperGoal, tasks: Task[]): number {
  if (superGoal.tasks.length === 0) return 0;
  const totalWeight = superGoal.tasks.reduce((sum, sgt) => sum + sgt.weight, 0);
  if (totalWeight === 0) return 0;

  let weightedScore = 0;
  let matchedTasks = 0;

  for (const sgt of superGoal.tasks) {
    const task = tasks.find(t => t.id === sgt.task_id);
    if (!task) continue;
    matchedTasks++;

    // Completion rate for current period (0–1)
    const completionRate = task.target_per_period > 0
      ? Math.min(task.completions_this_period / task.target_per_period, 1)
      : 0;

    // Streak consistency factor (0–1, maxes at 30 days)
    const streakFactor = Math.min(task.current_streak / 30, 1);

    // Task score: 65% current completion + 35% streak consistency
    const taskScore = completionRate * 0.65 + streakFactor * 0.35;

    weightedScore += (sgt.weight / totalWeight) * taskScore;
  }

  if (matchedTasks === 0) return 0;

  // Scale to percentage, clamp 1–99 (never 0% or 100%)
  const raw = Math.round(weightedScore * 100);
  return Math.max(1, Math.min(99, raw));
}

function getProbabilityColor(prob: number): string {
  if (prob >= 70) return '#22c55e';
  if (prob >= 40) return '#eab308';
  return '#ef4444';
}

function getProbabilityLabel(prob: number): string {
  if (prob >= 80) return 'Looking great!';
  if (prob >= 60) return 'On track';
  if (prob >= 40) return 'Making progress';
  if (prob >= 20) return 'Getting started';
  return 'Keep going';
}

// Probability Gauge (SVG circle)
function ProbabilityGauge({ probability }: { probability: number }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const progress = (probability / 100) * circumference;
  const color = getProbabilityColor(probability);

  return (
    <svg width="130" height="130" viewBox="0 0 130 130" className="super-goal-gauge">
      <circle cx="65" cy="65" r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="8" />
      <circle
        cx="65" cy="65" r={radius} fill="none"
        stroke={color} strokeWidth="8"
        strokeDasharray={circumference}
        strokeDashoffset={circumference - progress}
        strokeLinecap="round"
        transform="rotate(-90 65 65)"
        style={{ transition: 'stroke-dashoffset 0.6s ease' }}
      />
      <text x="65" y="58" textAnchor="middle" fill="#f8fafc" fontSize="26" fontWeight="700">
        {probability}%
      </text>
      <text x="65" y="78" textAnchor="middle" fill="#94a3b8" fontSize="10" fontWeight="500">
        estimated
      </text>
    </svg>
  );
}

// Super Goal Card component
function SuperGoalCard({
  goal, tasks, onEdit, onDelete
}: {
  goal: SuperGoal;
  tasks: Task[];
  onEdit: (goal: SuperGoal) => void;
  onDelete: (goalId: number) => void;
}) {
  const probability = calculateSuperGoalProbability(goal, tasks);
  const totalWeight = goal.tasks.reduce((s, t) => s + t.weight, 0);

  return (
    <div className="super-goal-card">
      <div className="super-goal-actions-top">
        <button onClick={() => onEdit(goal)} title="Edit">✏️</button>
        <button className="delete-btn" onClick={() => { if (confirm('Delete this Super Goal?')) onDelete(goal.id); }} title="Delete">🗑️</button>
      </div>

      <div className="super-goal-header">
        <ProbabilityGauge probability={probability} />
        <div className="super-goal-info">
          <h3>{goal.icon} {goal.name}</h3>
          {goal.description && <p>{goal.description}</p>}
          <div style={{ marginTop: '8px', fontSize: '0.78rem', fontWeight: 600, color: getProbabilityColor(probability) }}>
            {getProbabilityLabel(probability)}
          </div>
        </div>
      </div>

      <div className="super-goal-tasks-list">
        {goal.tasks.map(sgt => {
          const task = tasks.find(t => t.id === sgt.task_id);
          if (!task) return null;
          const { name, emoji } = getTaskDisplay(task);
          const pct = task.target_per_period > 0
            ? Math.round((task.completions_this_period / task.target_per_period) * 100)
            : 0;
          const statusClass = pct >= 100 ? 'complete' : pct >= 50 ? 'partial' : 'behind';
          const weightPct = totalWeight > 0 ? Math.round((sgt.weight / totalWeight) * 100) : 0;

          return (
            <div key={sgt.task_id} className="sg-task-row">
              <span className="sg-task-emoji">{emoji}</span>
              <span className="sg-task-name">{name}</span>
              <span className="sg-task-weight-badge">{weightPct}%</span>
              <span className={`sg-task-status ${statusClass}`}>{pct}%</span>
            </div>
          );
        })}
      </div>

      <div className="sg-disclaimer">
        <strong>Fun indicator only</strong> — this probability is a motivational estimate based on your
        current consistency, not a statistical guarantee. Keep showing up and your odds keep climbing!
      </div>
    </div>
  );
}

// Super Goal Form (create / edit modal)
function SuperGoalForm({
  tasks, existingGoal, onSave, onCancel, discordId, appUserId
}: {
  tasks: Task[];
  existingGoal: SuperGoal | null;
  onSave: (goals: SuperGoal[]) => void;
  onCancel: () => void;
  discordId: string;
  appUserId: number | null;
}) {
  const [name, setName] = useState(existingGoal?.name || '');
  const [description, setDescription] = useState(existingGoal?.description || '');
  const [icon, setIcon] = useState(existingGoal?.icon || '🎯');
  const [saving, setSaving] = useState(false);

  // Task weights: Map<taskId, { selected: boolean, weight: number }>
  const initWeights: Record<number, { selected: boolean; weight: number }> = {};
  for (const t of tasks) {
    const existing = existingGoal?.tasks.find(sgt => sgt.task_id === t.id);
    initWeights[t.id] = { selected: !!existing, weight: existing?.weight || 10 };
  }
  const [taskWeights, setTaskWeights] = useState(initWeights);

  const selectedCount = Object.values(taskWeights).filter(v => v.selected).length;
  const totalWeight = Object.values(taskWeights).filter(v => v.selected).reduce((s, v) => s + v.weight, 0);

  const toggleTask = (taskId: number) => {
    setTaskWeights(prev => ({
      ...prev,
      [taskId]: { ...prev[taskId], selected: !prev[taskId].selected }
    }));
  };

  const setWeight = (taskId: number, weight: number) => {
    setTaskWeights(prev => ({
      ...prev,
      [taskId]: { ...prev[taskId], weight }
    }));
  };

  const handleSave = async () => {
    if (!name.trim()) return;
    if (selectedCount < 2) return;

    setSaving(true);
    try {
      const taskWeightArr = Object.entries(taskWeights)
        .filter(([, v]) => v.selected)
        .map(([id, v]) => ({ task_id: parseInt(id), weight: v.weight }));

      const body: Record<string, unknown> = {
        action: existingGoal ? 'update_tasks' : 'create',
        name: name.trim(),
        description: description.trim() || null,
        icon,
        task_weights: taskWeightArr,
      };
      if (existingGoal) body.super_goal_id = existingGoal.id;
      if (appUserId) body.app_user_id = appUserId;
      if (discordId) body.discord_id = discordId;

      // If editing, also update name/description/icon
      if (existingGoal) {
        const updateBody: Record<string, unknown> = {
          action: 'update',
          super_goal_id: existingGoal.id,
          name: name.trim(),
          description: description.trim() || null,
          icon,
        };
        if (appUserId) updateBody.app_user_id = appUserId;
        if (discordId) updateBody.discord_id = discordId;

        await fetch(`${getApiBase()}/accountability/super_goals.php`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updateBody),
        });
      }

      const response = await fetch(`${getApiBase()}/accountability/super_goals.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = await response.json();
      if (result.error) throw new Error(result.error);
      if (result.super_goals) onSave(result.super_goals);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save super goal');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="sg-form-overlay" onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="sg-form-card">
        <h2>{existingGoal ? 'Edit Super Goal' : 'Create Super Goal'}</h2>

        <div className="sg-form-group">
          <label>Goal Name *</label>
          <input
            type="text" value={name} onChange={e => setName(e.target.value)}
            placeholder="e.g. Get Healthier, Launch Side Project"
            maxLength={100}
          />
        </div>

        <div className="sg-form-group">
          <label>Description (optional)</label>
          <textarea
            value={description} onChange={e => setDescription(e.target.value)}
            placeholder="What does achieving this look like?"
            maxLength={300}
          />
        </div>

        <div className="sg-form-group">
          <label>Icon</label>
          <div className="sg-icon-picker">
            {SUPER_GOAL_ICONS.map(ic => (
              <button
                key={ic}
                className={`sg-icon-option ${icon === ic ? 'selected' : ''}`}
                onClick={() => setIcon(ic)}
                type="button"
              >
                {ic}
              </button>
            ))}
          </div>
        </div>

        <div className="sg-form-group">
          <label>Link Tasks &amp; Set Weights (min. 2)</label>
          {tasks.length === 0 ? (
            <p style={{ fontSize: '0.82rem', color: '#64748b' }}>No tasks to link. Create some tasks first!</p>
          ) : (
            <div className="sg-task-picker">
              {tasks.filter(t => !t.is_paused).map(task => {
                const { name: tName, emoji } = getTaskDisplay(task);
                const tw = taskWeights[task.id];
                return (
                  <div key={task.id} className={`sg-task-picker-row ${tw?.selected ? 'selected' : ''}`}>
                    <input
                      type="checkbox"
                      className="sg-task-picker-checkbox"
                      checked={tw?.selected || false}
                      onChange={() => toggleTask(task.id)}
                    />
                    <span style={{ fontSize: '1rem' }}>{emoji}</span>
                    <span className="sg-task-picker-name">{tName}</span>
                    {tw?.selected && (
                      <div className="sg-task-picker-weight">
                        <input
                          type="range" min={1} max={50} value={tw.weight}
                          onChange={e => setWeight(task.id, parseInt(e.target.value))}
                        />
                        <span>{totalWeight > 0 ? Math.round((tw.weight / totalWeight) * 100) : 0}%</span>
                      </div>
                    )}
                  </div>
                );
              })}
              {selectedCount >= 2 && (
                <div className="sg-weight-total">
                  <span className="total-label">Weights automatically normalized to 100%</span>
                  <span className={`total-value balanced`}>{selectedCount} tasks selected</span>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="sg-form-actions">
          <button className="sg-cancel-btn" onClick={onCancel} type="button">Cancel</button>
          <button
            className="sg-save-btn"
            onClick={handleSave}
            disabled={saving || !name.trim() || selectedCount < 2}
          >
            {saving ? 'Saving...' : existingGoal ? 'Save Changes' : 'Create Super Goal'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AccountabilityDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [discordId, setDiscordId] = useState<string>('');
  const [appUserId, setAppUserId] = useState<number | null>(null);
  const [isLinked, setIsLinked] = useState(false);
  const [authMode, setAuthMode] = useState<'discord' | 'app' | null>(null);
  const [checkinLoading, setCheckinLoading] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'tasks' | 'goals' | 'score' | 'insights' | 'history'>('tasks');
  const [showSetupForm, setShowSetupForm] = useState(false);
  
  // Super Goals state
  const [superGoals, setSuperGoals] = useState<SuperGoal[]>([]);
  const [showSuperGoalForm, setShowSuperGoalForm] = useState(false);
  const [editingSuperGoal, setEditingSuperGoal] = useState<SuperGoal | null>(null);

  // Pattern Finder state
  const [detectedPatterns, setDetectedPatterns] = useState<DetectedPattern[]>([]);
  const [patternsLoading, setPatternsLoading] = useState(false);
  
  // Morning follow-up opt-out state
  const [followupOptedOut, setFollowupOptedOut] = useState<boolean | null>(null);
  const [followupToggling, setFollowupToggling] = useState(false);

  // Toast notifications
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  
  // Notification polling
  const pollingRef = useRef<number | null>(null);
  const [notifPermission, setNotifPermission] = useState<NotificationPermission>(
    typeof Notification !== 'undefined' ? Notification.permission : 'default'
  );
  
  // Add toast helper
  const addToast = useCallback((title: string, body: string, type: ToastItem['type'] = 'info') => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts(prev => [...prev.slice(-4), { id, title, body, type, timestamp: Date.now() }]);
    // Auto dismiss after 5 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);
  
  // Check for auth on mount
  useEffect(() => {
    // 1. Check standalone accountability storage first
    const standalone = localStorage.getItem('accountability_discord_id');
    if (standalone) {
      setDiscordId(standalone);
      setAuthMode('discord');
      setIsLinked(true);
      return;
    }
    
    // 2. Check main app auth
    try {
      const authRaw = localStorage.getItem('fav_creators_auth_user');
      if (authRaw) {
        const authUser = JSON.parse(authRaw);
        if (authUser) {
          // If they have a discord_id linked, use that
          if (authUser.discord_id) {
            setDiscordId(authUser.discord_id);
            setAuthMode('discord');
            setIsLinked(true);
            // Also store app user id for web features
            if (authUser.id) setAppUserId(authUser.id);
            return;
          }
          // Web-only user (no Discord linked) - use app_user_id
          if (authUser.id) {
            setAppUserId(authUser.id);
            setAuthMode('app');
            setIsLinked(true);
            return;
          }
        }
      }
    } catch {
      // ignore parse errors
    }
    
    setLoading(false);
  }, []);
  
  // Fetch dashboard data
  const fetchDashboard = useCallback(async () => {
    if (!discordId && !appUserId) {
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      let url = `${getApiBase()}/accountability/dashboard.php?`;
      if (appUserId) url += `app_user_id=${appUserId}`;
      if (discordId) url += `${appUserId ? '&' : ''}discord_id=${discordId}`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch dashboard: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.error) {
        // If user not found for web-only user, show setup form instead of error
        if (authMode === 'app' && result.error.includes('not found')) {
          setData(null);
          setShowSetupForm(true);
          setLoading(false);
          return;
        }
        throw new Error(result.error);
      }
      
      setData(result);
      setShowSetupForm(false);
      
      // Fetch super goals alongside dashboard
      fetchSuperGoals();
    } catch (err) {
      // For app users with no account, show setup instead of error
      if (authMode === 'app') {
        setData(null);
        setShowSetupForm(true);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard');
      }
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId, appUserId, authMode]);

  // Fetch super goals
  const fetchSuperGoals = useCallback(async () => {
    if (!discordId && !appUserId) return;
    try {
      let url = `${getApiBase()}/accountability/super_goals.php?`;
      if (appUserId) url += `app_user_id=${appUserId}`;
      if (discordId) url += `${appUserId ? '&' : ''}discord_id=${discordId}`;
      const response = await fetch(url);
      if (!response.ok) return;
      const result = await response.json();
      if (result.super_goals) setSuperGoals(result.super_goals);
    } catch {
      // silent fail — super goals are optional
    }
  }, [discordId, appUserId]);
  
  useEffect(() => {
    if (isLinked && (discordId || appUserId)) {
      fetchDashboard();
    }
  }, [isLinked, discordId, appUserId, fetchDashboard]);

  // Load patterns when Insights tab is first opened
  useEffect(() => {
    if (activeTab === 'insights' && detectedPatterns.length === 0 && !patternsLoading && isLinked) {
      fetchPatterns();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, isLinked]);
  
  // Notification polling
  const pollNotifications = useCallback(async () => {
    if (!appUserId && !discordId) return;
    
    try {
      let url = `${getApiBase()}/accountability/web_notifications.php?`;
      if (appUserId) url += `app_user_id=${appUserId}`;
      else if (discordId) url += `discord_id=${discordId}`;
      
      const response = await fetch(url);
      if (!response.ok) return;
      
      const result = await response.json();
      if (!result.notifications || result.notifications.length === 0) return;
      
      const notifications: WebNotification[] = result.notifications;
      const idsToMark: number[] = [];
      
      for (const notif of notifications) {
        // Show as in-app toast
        const toastType = notif.type === 'warning' ? 'warning' : notif.type === 'celebration' ? 'celebration' : 'info';
        addToast(notif.title, notif.body, toastType as ToastItem['type']);
        
        // If tab is not focused and browser notifications enabled, show browser notification
        if (document.hidden && notifPermission === 'granted') {
          try {
            new Notification(notif.title, {
              body: notif.body,
              icon: '/fc/favicon.ico',
              tag: `acc-notif-${notif.id}`,
            });
          } catch {
            // Notification API might fail silently
          }
        }
        
        idsToMark.push(notif.id);
      }
      
      // Mark as read
      if (idsToMark.length > 0) {
        fetch(`${getApiBase()}/accountability/web_notifications.php`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mark_read: idsToMark }),
        }).catch(() => {});
      }
    } catch {
      // Silent fail for polling
    }
  }, [appUserId, discordId, addToast, notifPermission]);
  
  // Start polling when dashboard is loaded
  useEffect(() => {
    if (!isLinked || (!appUserId && !discordId)) return;
    
    // Initial poll after 2 seconds
    const initialTimer = setTimeout(pollNotifications, 2000);
    
    // Poll every 60 seconds
    pollingRef.current = window.setInterval(pollNotifications, 60000);
    
    return () => {
      clearTimeout(initialTimer);
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [isLinked, appUserId, discordId, pollNotifications]);
  
  // Fetch morning follow-up opt-out status
  useEffect(() => {
    if (!isLinked || (!appUserId && !discordId)) return;
    let url = `${getApiBase()}/accountability/goal_followup_optout.php?check=1`;
    if (appUserId) url += `&app_user_id=${appUserId}`;
    if (discordId) url += `&discord_id=${discordId}`;
    fetch(url)
      .then(r => r.json())
      .then(result => {
        if (result.success) setFollowupOptedOut(result.opted_out);
      })
      .catch(() => {});
  }, [isLinked, appUserId, discordId]);

  // Toggle morning follow-up
  const handleToggleFollowup = async () => {
    if (followupToggling) return;
    setFollowupToggling(true);
    const newAction = followupOptedOut ? 'optin' : 'optout';
    try {
      const body: Record<string, unknown> = { action: newAction };
      if (appUserId) body.app_user_id = appUserId;
      if (discordId) body.discord_id = discordId;
      const resp = await fetch(`${getApiBase()}/accountability/goal_followup_optout.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = await resp.json();
      if (result.success) {
        setFollowupOptedOut(result.opted_out);
        addToast(
          result.opted_out ? 'Morning Follow-ups Stopped' : 'Morning Follow-ups Enabled',
          result.opted_out
            ? 'You will no longer receive 9 AM goal follow-up DMs.'
            : 'You will receive a daily 9 AM EST DM with your goal summary.',
          result.opted_out ? 'info' : 'success'
        );
      }
    } catch {
      addToast('Error', 'Failed to update follow-up preference.', 'warning');
    } finally {
      setFollowupToggling(false);
    }
  };

  // Handle Discord ID submission
  const handleLink = (e: React.FormEvent) => {
    e.preventDefault();
    if (discordId.trim()) {
      localStorage.setItem('accountability_discord_id', discordId.trim());
      setAuthMode('discord');
      setIsLinked(true);
    }
  };
  
  // Handle unlink
  const handleUnlink = () => {
    localStorage.removeItem('accountability_discord_id');
    setDiscordId('');
    setAppUserId(null);
    setAuthMode(null);
    setIsLinked(false);
    setData(null);
    setShowSetupForm(false);
  };
  
  // Handle check-in (now accepts optional notes)
  const handleCheckin = async (taskId: number, notes?: string) => {
    if (!discordId && !appUserId) return;
    
    try {
      setCheckinLoading(taskId);
      
      const body: Record<string, unknown> = { task_id: taskId };
      if (appUserId) body.app_user_id = appUserId;
      if (discordId) body.discord_id = discordId;
      if (notes) body.notes = notes;
      
      const response = await fetch(`${getApiBase()}/accountability/checkin.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      
      const result = await response.json();
      
      if (result.error) {
        throw new Error(result.error);
      }
      
      // Show success toast
      if (result.success) {
        addToast(
          'Check-in logged!',
          `${result.task_name}: ${result.completions}/${result.target}${result.period_complete ? ' - Period complete!' : ''}`,
          result.period_complete ? 'celebration' : 'success'
        );
      }
      
      await fetchDashboard();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Check-in failed');
    } finally {
      setCheckinLoading(null);
    }
  };

  const handleNotifPermissionGrant = () => {
    setNotifPermission('granted');
    addToast('Notifications Enabled', 'You will now receive browser notifications for your accountability reminders.', 'success');
  };

  // Super Goal handlers
  const handleDeleteSuperGoal = async (goalId: number) => {
    try {
      const body: Record<string, unknown> = { action: 'delete', super_goal_id: goalId };
      if (appUserId) body.app_user_id = appUserId;
      if (discordId) body.discord_id = discordId;

      const response = await fetch(`${getApiBase()}/accountability/super_goals.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = await response.json();
      if (result.super_goals) setSuperGoals(result.super_goals);
      addToast('Deleted', 'Super Goal removed.', 'info');
    } catch {
      addToast('Error', 'Failed to delete super goal.', 'warning');
    }
  };

  const handleSuperGoalSaved = (goals: SuperGoal[]) => {
    setSuperGoals(goals);
    setShowSuperGoalForm(false);
    setEditingSuperGoal(null);
    addToast('Saved!', 'Super Goal updated.', 'success');
  };

  // Pattern Finder handlers
  const fetchPatterns = useCallback(async (refresh = false) => {
    if (!discordId && !appUserId) return;
    setPatternsLoading(true);
    try {
      let url = `${getApiBase()}/accountability/patterns.php?`;
      if (appUserId) url += `app_user_id=${appUserId}`;
      if (discordId) url += `${appUserId ? '&' : ''}discord_id=${discordId}`;
      if (refresh) url += '&refresh=1';
      const resp = await fetch(url);
      if (!resp.ok) return;
      const result = await resp.json();
      if (result.patterns) setDetectedPatterns(result.patterns);
    } catch {
      // silent
    } finally {
      setPatternsLoading(false);
    }
  }, [discordId, appUserId]);

  const handleDetectPatterns = async () => {
    if (!discordId && !appUserId) return;
    setPatternsLoading(true);
    try {
      const body: Record<string, unknown> = { action: 'detect' };
      if (appUserId) body.app_user_id = appUserId;
      if (discordId) body.discord_id = discordId;
      const resp = await fetch(`${getApiBase()}/accountability/patterns.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = await resp.json();
      if (result.patterns) {
        setDetectedPatterns(result.patterns);
        addToast('Patterns Updated', `Found ${result.patterns_found || 0} correlations in your data.`, 'info');
      }
    } catch {
      addToast('Error', 'Failed to detect patterns.', 'warning');
    } finally {
      setPatternsLoading(false);
    }
  };

  const handleRatePattern = async (patternId: number, rating: 'helpful' | 'not_helpful' | null) => {
    const body: Record<string, unknown> = { action: 'rate', pattern_id: patternId, rating };
    if (appUserId) body.app_user_id = appUserId;
    if (discordId) body.discord_id = discordId;
    try {
      const resp = await fetch(`${getApiBase()}/accountability/patterns.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = await resp.json();
      if (result.patterns) setDetectedPatterns(result.patterns);
    } catch { /* silent */ }
  };

  const handleDismissPattern = async (patternId: number) => {
    const body: Record<string, unknown> = { action: 'dismiss', pattern_id: patternId };
    if (appUserId) body.app_user_id = appUserId;
    if (discordId) body.discord_id = discordId;
    try {
      const resp = await fetch(`${getApiBase()}/accountability/patterns.php`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = await resp.json();
      if (result.patterns) setDetectedPatterns(result.patterns);
      addToast('Dismissed', 'Pattern hidden from view.', 'info');
    } catch { /* silent */ }
  };
  
  // Not linked state - show Discord bot showcase + login
  if (!isLinked) {
    const cmdSectionStyle: React.CSSProperties = {
      background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: '12px', marginBottom: '8px', overflow: 'hidden',
    };
    const cmdSummaryStyle: React.CSSProperties = {
      cursor: 'pointer', padding: '14px 18px', fontSize: '0.92rem', fontWeight: 600,
      color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '10px',
      listStyle: 'none', userSelect: 'none',
    };
    const cmdBodyStyle: React.CSSProperties = {
      padding: '0 18px 16px', fontSize: '0.82rem', color: '#94a3b8', lineHeight: 1.6,
    };
    const cmdCodeStyle: React.CSSProperties = {
      background: 'rgba(88,101,242,0.12)', color: '#7c8af6', padding: '2px 7px',
      borderRadius: '4px', fontFamily: 'monospace', fontSize: '0.8rem', fontWeight: 600,
    };
    const exampleBlockStyle: React.CSSProperties = {
      background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px',
      padding: '10px 14px', margin: '8px 0', fontFamily: 'monospace', fontSize: '0.78rem',
      color: '#94a3b8',
    };
    const cmdTextStyle: React.CSSProperties = { color: '#7c8af6', fontWeight: 600 };
    const responseStyle: React.CSSProperties = { color: '#64748b', fontStyle: 'italic', marginTop: '4px' };
    const featureGridStyle: React.CSSProperties = {
      display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
      gap: '12px', margin: '16px 0',
    };
    const featureCardStyle: React.CSSProperties = {
      background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: '12px', padding: '16px', textAlign: 'center',
    };

    return (
      <div className="accountability-dashboard">
        <ToastContainer toasts={toasts} onDismiss={dismissToast} />
        <div style={{ maxWidth: '780px', margin: '0 auto', padding: '24px 0' }}>

          {/* Hero */}
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <div style={{
              display: 'inline-block', background: 'rgba(88,101,242,0.15)', border: '1px solid rgba(88,101,242,0.3)',
              borderRadius: '20px', padding: '5px 14px', fontSize: '0.72rem', color: '#7c8af6',
              fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '12px',
            }}>
              Discord Bot + Web Dashboard
            </div>
            <h1 style={{
              fontSize: 'clamp(1.6rem, 4vw, 2.2rem)', fontWeight: 800, margin: '0 0 8px',
              background: 'linear-gradient(135deg, #60a5fa, #a78bfa)', WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent', backgroundClip: 'text',
            }}>
              FindTorontoEvents Bot
            </h1>
            <p style={{ color: '#94a3b8', maxWidth: '550px', margin: '0 auto 20px', lineHeight: 1.6 }}>
              31 slash commands covering events, weather, stocks, movies, mental health, and a full accountability coach &mdash; all from Discord or this web dashboard.
            </p>
          </div>

          {/* Quick feature highlights */}
          <div style={featureGridStyle}>
            {[
              { icon: '🧥', title: 'Need a Jacket?', desc: 'Instant weather advice before heading out' },
              { icon: '🎯', title: 'Accountability Coach', desc: 'Habit tracking, streaks, reminders & score' },
              { icon: '📅', title: 'Toronto Events', desc: 'Search events, get notified about new ones' },
              { icon: '📈', title: 'Stock Picks', desc: 'AI-validated stock picks with alerts' },
              { icon: '🎬', title: 'Movies & TV', desc: 'New releases, trailers, and search' },
              { icon: '💚', title: 'Mental Health', desc: 'Crisis resources, breathing exercises, grounding' },
            ].map(f => (
              <div key={f.title} style={featureCardStyle}>
                <div style={{ fontSize: '1.6rem', marginBottom: '6px' }}>{f.icon}</div>
                <div style={{ fontWeight: 700, color: '#f1f5f9', fontSize: '0.88rem', marginBottom: '4px' }}>{f.title}</div>
                <div style={{ fontSize: '0.78rem', color: '#64748b' }}>{f.desc}</div>
              </div>
            ))}
          </div>

          {/* CTA - Get Started */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(88,101,242,0.1), rgba(168,85,247,0.1))',
            border: '1px solid rgba(88,101,242,0.25)', borderRadius: '16px',
            padding: '24px', textAlign: 'center', marginBottom: '24px',
          }}>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '8px' }}>
              Get Started
            </h2>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '16px', lineHeight: 1.5 }}>
              <a href="#/guest" style={{ color: '#5865F2', textDecoration: 'none', fontWeight: 700 }}>
                Log into FavCreators
              </a>
              {' '}to use the web dashboard, or add our bot to Discord with{' '}
              <span style={cmdCodeStyle}>/fc-help</span> to see all commands.
            </p>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
              <a href="#/guest" style={{
                padding: '10px 24px', background: '#5865F2', color: '#fff', fontWeight: 700,
                borderRadius: '10px', textDecoration: 'none', fontSize: '0.88rem',
              }}>
                Log In / Sign Up
              </a>
              <a href="https://discord.com/oauth2/authorize?client_id=1469428932980899974&permissions=2048&scope=bot%20applications.commands" target="_blank" rel="noopener noreferrer" style={{
                padding: '10px 24px', background: 'rgba(88,101,242,0.15)', color: '#7c8af6', fontWeight: 700,
                borderRadius: '10px', textDecoration: 'none', fontSize: '0.88rem',
                border: '1px solid rgba(88,101,242,0.3)',
              }}>
                Add Bot to Discord
              </a>
            </div>
            <details style={{ marginTop: '14px', textAlign: 'left' }}>
              <summary style={{ cursor: 'pointer', color: '#64748b', fontSize: '0.78rem', fontWeight: 600, textAlign: 'center' }}>
                Or enter your Discord ID manually...
              </summary>
              <form onSubmit={handleLink} className="link-form" style={{ marginTop: '0.75rem' }}>
                <div className="input-group">
                  <label htmlFor="discord-id">Discord User ID</label>
                  <input id="discord-id" type="text" value={discordId} onChange={(e) => setDiscordId(e.target.value)}
                    placeholder="Enter your Discord user ID" pattern="[0-9]+" required />
                  <small>Enable Developer Mode in Discord settings, right-click your username → "Copy User ID"</small>
                </div>
                <button type="submit" className="link-button">View Dashboard</button>
              </form>
            </details>
          </div>

          {/* All Commands - Collapsible Sections */}
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '12px' }}>
            All Bot Commands
          </h2>
          <p style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: '16px' }}>
            Type <span style={cmdCodeStyle}>/fc-</span> in any Discord channel to see autocomplete. Click any section below to expand.
          </p>

          {/* Weather */}
          <details style={cmdSectionStyle}>
            <summary style={cmdSummaryStyle}><span>🌤️</span> Weather &amp; Jacket Check <span style={{marginLeft:'auto',fontSize:'0.7rem',color:'#64748b'}}>2 commands</span></summary>
            <div style={cmdBodyStyle}>
              <p>Check the weather or get a quick "do I need a jacket?" answer before heading out.</p>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-jacket location:</span> Toronto</div>
                <div style={responseStyle}>→ "🧥 Yes, bring a jacket! It's 2°C with wind chill -5°C. Feels like winter out there."</div>
              </div>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-weather location:</span> Toronto</div>
                <div style={responseStyle}>→ Full weather report with RealFeel, wind, precipitation alerts, and hourly forecast</div>
              </div>
              <p style={{marginTop:'8px'}}>Works for any city — try "New York", "Vancouver", "London", etc.</p>
            </div>
          </details>

          {/* Accountability Coach */}
          <details style={cmdSectionStyle} open>
            <summary style={cmdSummaryStyle}><span>🏋️</span> Accountability Coach <span style={{marginLeft:'auto',fontSize:'0.7rem',color:'#64748b'}}>6 commands</span></summary>
            <div style={cmdBodyStyle}>
              <p>A full habit-tracking system with streaks, reminders, scoring, and coach personalities.</p>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-coach action:</span> setup <span style={cmdTextStyle}>taskname:</span> gym</div>
                <div style={responseStyle}>→ Creates a gym task with automatic reminders, streak tracking, and shield protection</div>
              </div>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-coach action:</span> checkin <span style={cmdTextStyle}>taskname:</span> gym</div>
                <div style={responseStyle}>→ "✅ Checked in! Streak: 14 days 🥈 Silver tier. Keep it up!"</div>
              </div>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-status</span></div>
                <div style={responseStyle}>→ Full overview: all tasks, progress, actions needed, next reminders, streak tiers</div>
              </div>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-score</span></div>
                <div style={responseStyle}>→ Accountability score breakdown: completion, consistency, discipline (week/month/year)</div>
              </div>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-gym exercise:</span> bench press <span style={cmdTextStyle}>weight:</span> 135 <span style={cmdTextStyle}>reps:</span> 8 <span style={cmdTextStyle}>sets:</span> 3</div>
                <div style={responseStyle}>→ Logs detailed workout with exercise tracking and history</div>
              </div>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-timer action:</span> start <span style={cmdTextStyle}>taskname:</span> meditation <span style={cmdTextStyle}>minutes:</span> 15</div>
                <div style={responseStyle}>→ Starts a 15-minute timer, notifies you when it's done</div>
              </div>
              <p style={{marginTop:'8px'}}>
                <strong style={{color:'#e2e8f0'}}>20+ task templates:</strong> gym, meditation, reading, cleaning, shower, journaling, water, sleep, meals, gratitude, and more.
                <br/>
                <strong style={{color:'#e2e8f0'}}>5 coach personalities:</strong> Default, Supportive, Drill Sergeant, Stoic, and Chaos Goblin.
              </p>
            </div>
          </details>

          {/* Events */}
          <details style={cmdSectionStyle}>
            <summary style={cmdSummaryStyle}><span>📅</span> Toronto Events <span style={{marginLeft:'auto',fontSize:'0.7rem',color:'#64748b'}}>5 commands</span></summary>
            <div style={cmdBodyStyle}>
              <p>Search for Toronto events and subscribe to categories for automatic notifications.</p>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-events search:</span> concerts <span style={cmdTextStyle}>when:</span> this weekend</div>
                <div style={responseStyle}>→ Lists upcoming concerts this weekend with dates, venues, and links</div>
              </div>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-subscribe category:</span> dating <span style={cmdTextStyle}>frequency:</span> weekly</div>
                <div style={responseStyle}>→ "Subscribed! You'll get weekly dating event roundups every Monday."</div>
              </div>
              <p style={{marginTop:'8px'}}>
                <span style={cmdCodeStyle}>/fc-myevents</span> — see your saved events &nbsp;|&nbsp;
                <span style={cmdCodeStyle}>/fc-mysubs</span> — manage subscriptions &nbsp;|&nbsp;
                <span style={cmdCodeStyle}>/fc-unsubscribe</span> — stop notifications
              </p>
            </div>
          </details>

          {/* Stocks */}
          <details style={cmdSectionStyle}>
            <summary style={cmdSummaryStyle}><span>📈</span> Stock Picks &amp; Alerts <span style={{marginLeft:'auto',fontSize:'0.7rem',color:'#64748b'}}>6 commands</span></summary>
            <div style={cmdBodyStyle}>
              <p>View AI-validated stock picks, get price details, and subscribe to alerts for specific tickers.</p>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-stocks rating:</span> strong_buy</div>
                <div style={responseStyle}>→ Lists today's strong buy picks with ratings, price targets, and analysis</div>
              </div>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-stocksub symbol:</span> NVDA</div>
                <div style={responseStyle}>→ "Subscribed to NVDA! You'll be notified when it's picked."</div>
              </div>
              <p style={{marginTop:'8px'}}>
                <span style={cmdCodeStyle}>/fc-stock AAPL</span> — stock details &nbsp;|&nbsp;
                <span style={cmdCodeStyle}>/fc-stockperf</span> — performance stats &nbsp;|&nbsp;
                <span style={cmdCodeStyle}>/fc-mystocks</span> — your subscriptions
              </p>
            </div>
          </details>

          {/* Movies */}
          <details style={cmdSectionStyle}>
            <summary style={cmdSummaryStyle}><span>🎬</span> Movies &amp; TV Shows <span style={{marginLeft:'auto',fontSize:'0.7rem',color:'#64748b'}}>3 commands</span></summary>
            <div style={cmdBodyStyle}>
              <p>Search movies & shows, browse new releases, and get trailers instantly.</p>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-movies search:</span> inception <span style={cmdTextStyle}>type:</span> movie</div>
                <div style={responseStyle}>→ Movie details: rating, release date, cast, synopsis, where to watch</div>
              </div>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-trailers title:</span> The Last of Us</div>
                <div style={responseStyle}>→ Embedded trailer link ready to watch</div>
              </div>
              <p style={{marginTop:'8px'}}>
                <span style={cmdCodeStyle}>/fc-newreleases type: movie period: week</span> — what's new this week
              </p>
            </div>
          </details>

          {/* Creators */}
          <details style={cmdSectionStyle}>
            <summary style={cmdSummaryStyle}><span>🎭</span> Creator Tracking <span style={{marginLeft:'auto',fontSize:'0.7rem',color:'#64748b'}}>4 commands</span></summary>
            <div style={cmdBodyStyle}>
              <p>Track your favorite streamers and content creators across Twitch, YouTube, Kick, and more.</p>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-live</span></div>
                <div style={responseStyle}>→ Shows all tracked creators currently streaming with viewer counts and platforms</div>
              </div>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-posts creator:</span> Ludwig <span style={cmdTextStyle}>count:</span> 5</div>
                <div style={responseStyle}>→ Latest 5 posts/videos from Ludwig across all platforms</div>
              </div>
              <p style={{marginTop:'8px'}}>
                <span style={cmdCodeStyle}>/fc-creators</span> — list tracked creators &nbsp;|&nbsp;
                <span style={cmdCodeStyle}>/fc-about</span> — creator info &amp; stats
              </p>
            </div>
          </details>

          {/* Mental Health */}
          <details style={cmdSectionStyle}>
            <summary style={cmdSummaryStyle}><span>💚</span> Mental Health Resources <span style={{marginLeft:'auto',fontSize:'0.7rem',color:'#64748b'}}>1 command</span></summary>
            <div style={cmdBodyStyle}>
              <p>Instant access to mental health resources including crisis lines, breathing exercises, and grounding techniques.</p>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-mentalhealth topic:</span> breathing</div>
                <div style={responseStyle}>→ Guided breathing exercise: 4-7-8 technique with step-by-step instructions</div>
              </div>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-mentalhealth topic:</span> crisis</div>
                <div style={responseStyle}>→ Crisis hotline numbers, text lines, and immediate resources</div>
              </div>
              <p style={{marginTop:'8px'}}>
                Topics: <span style={cmdCodeStyle}>crisis</span> <span style={cmdCodeStyle}>breathing</span> <span style={cmdCodeStyle}>grounding</span> <span style={cmdCodeStyle}>panic</span> <span style={cmdCodeStyle}>games</span> <span style={cmdCodeStyle}>demographics</span>
                <br/>
                Full resource page: <a href="/MENTALHEALTHRESOURCES/" style={{color:'#22c55e',textDecoration:'underline'}}>Mental Health Resources</a>
              </p>
            </div>
          </details>

          {/* General / Settings */}
          <details style={cmdSectionStyle}>
            <summary style={cmdSummaryStyle}><span>⚙️</span> General &amp; Settings <span style={{marginLeft:'auto',fontSize:'0.7rem',color:'#64748b'}}>4 commands</span></summary>
            <div style={cmdBodyStyle}>
              <p>Account linking, notification preferences, and general info.</p>
              <div style={exampleBlockStyle}>
                <div><span style={cmdTextStyle}>/fc-notifymode mode:</span> dm</div>
                <div style={responseStyle}>→ "Notifications set to DM! You'll receive all alerts as direct messages."</div>
              </div>
              <p style={{marginTop:'8px'}}>
                <span style={cmdCodeStyle}>/fc-link</span> — link your Discord account &nbsp;|&nbsp;
                <span style={cmdCodeStyle}>/fc-info</span> — explore all site features &nbsp;|&nbsp;
                <span style={cmdCodeStyle}>/fc-help</span> — full command list
              </p>
            </div>
          </details>

          {/* Motivation page link */}
          <a href="/fc/motivation.html" target="_blank" rel="noopener noreferrer" style={{
            display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 16px', marginTop: '16px',
            background: 'linear-gradient(135deg, rgba(59,130,246,0.08), rgba(168,85,247,0.08))',
            border: '1px solid rgba(59,130,246,0.15)', borderRadius: '10px',
            color: '#94a3b8', fontSize: '0.82rem', textDecoration: 'none',
          }}>
            <span style={{ fontSize: '1.1rem' }}>🧠</span>
            <span><strong style={{ color: '#f1f5f9' }}>The Science of Showing Up</strong> — 10 research-backed techniques for motivation &amp; consistency</span>
            <span style={{ marginLeft: 'auto', color: '#3b82f6', fontWeight: 600, flexShrink: 0 }}>&rarr;</span>
          </a>

          {/* Footer */}
          <div style={{ textAlign: 'center', marginTop: '32px', color: '#475569', fontSize: '0.75rem' }}>
            <p>
              <a href="/" style={{color:'#64748b',textDecoration:'underline'}}>FindTorontoEvents</a> &middot;{' '}
              <a href="/fc/" style={{color:'#64748b',textDecoration:'underline'}}>FavCreators</a> &middot;{' '}
              <a href="/fc/motivation.html" style={{color:'#64748b',textDecoration:'underline'}}>Motivation Science</a>
            </p>
          </div>
        </div>
      </div>
    );
  }
  
  // Loading state
  if (loading) {
    return (
      <div className="accountability-dashboard">
        <div className="loading-container">
          <div className="loading-spinner">⏳</div>
          <p>Loading your dashboard...</p>
        </div>
      </div>
    );
  }
  
  // Error state (for discord users)
  if (error && !showSetupForm) {
    return (
      <div className="accountability-dashboard">
        <ToastContainer toasts={toasts} onDismiss={dismissToast} />
        <div className="error-container">
          <h2>Error</h2>
          <p>{error}</p>
          <div className="error-actions">
            <button onClick={fetchDashboard} className="retry-button">Retry</button>
            <button onClick={handleUnlink} className="unlink-button">Unlink Account</button>
          </div>
        </div>
      </div>
    );
  }
  
  // No data / setup form state (for web-only users)
  if (!data || showSetupForm) {
    return (
      <div className="accountability-dashboard">
        <ToastContainer toasts={toasts} onDismiss={dismissToast} />
        <header className="dashboard-header">
          <div className="header-content">
            <h1>🎯 Accountability Coach</h1>
            <div className="header-actions">
              <button onClick={handleUnlink} className="settings-btn" title="Switch account">⚙️</button>
            </div>
          </div>
          {appUserId && (
            <div className="user-info"><span>Web User #{appUserId}</span></div>
          )}
        </header>

        <NotificationPermissionBanner onGrant={handleNotifPermissionGrant} />

        <section className="section">
          {appUserId ? (
            <TaskSetupForm
              appUserId={appUserId}
              onTaskCreated={() => fetchDashboard()}
            />
          ) : (
            <div className="empty-container">
              <h2>Get Started</h2>
              <p>No accountability data found.</p>
              <p>Use <code>/fc-coach setup</code> in Discord to create your first task!</p>
              <button onClick={handleUnlink} className="unlink-button">Try Different Account</button>
            </div>
          )}
        </section>
        
        <footer className="dashboard-footer">
          <p><a href="#/guest">← Back to FavCreators</a></p>
        </footer>
      </div>
    );
  }
  
  return (
    <div className="accountability-dashboard">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1>🎯 Accountability Dashboard</h1>
          <div className="header-actions">
            <button onClick={() => setShowSetupForm(!showSetupForm)} className="refresh-btn" title="Add Task" style={{ fontSize: '1.1rem' }}>
              ➕
            </button>
            <button onClick={fetchDashboard} className="refresh-btn" title="Refresh">
              🔄
            </button>
            <button onClick={handleUnlink} className="settings-btn" title="Unlink">
              ⚙️
            </button>
          </div>
        </div>
        <div className="user-info">
          {data.user.discord_user_id && <><span>Discord: {data.user.discord_user_id}</span><span>•</span></>}
          {data.user.app_user_id && <><span>User #{data.user.app_user_id}</span><span>•</span></>}
          <span>{data.user.timezone}</span>
          {data.user.personality_mode !== 'default' && (
            <><span>•</span><span>Coach: {data.user.personality_mode}</span></>
          )}
        </div>
      </header>

      {/* Browser notification permission prompt */}
      <NotificationPermissionBanner onGrant={handleNotifPermissionGrant} />

      {/* Morning Follow-Up Toggle */}
      {followupOptedOut !== null && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '12px',
          padding: '12px 16px', marginBottom: '12px',
          background: followupOptedOut
            ? 'rgba(255,255,255,0.03)'
            : 'linear-gradient(135deg, rgba(16,185,129,0.08), rgba(59,130,246,0.08))',
          border: `1px solid ${followupOptedOut ? 'rgba(255,255,255,0.06)' : 'rgba(16,185,129,0.2)'}`,
          borderRadius: '10px',
          transition: 'all 0.2s',
        }}>
          <span style={{ fontSize: '1.3rem' }}>{followupOptedOut ? '🔕' : '☀️'}</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#f8fafc' }}>
              Morning Goal Follow-Up
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>
              {followupOptedOut
                ? 'Disabled — you won\'t receive daily 9 AM goal DMs'
                : 'Enabled — you get a DM at 9 AM EST each day with your goal summary & streaks'}
            </div>
          </div>
          <button
            onClick={handleToggleFollowup}
            disabled={followupToggling}
            style={{
              padding: '6px 14px', borderRadius: '6px', fontSize: '0.78rem', fontWeight: 600,
              border: 'none', cursor: followupToggling ? 'wait' : 'pointer',
              background: followupOptedOut ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.12)',
              color: followupOptedOut ? '#10b981' : '#f87171',
              transition: 'opacity 0.2s',
              opacity: followupToggling ? 0.5 : 1,
            }}
          >
            {followupToggling
              ? '...'
              : followupOptedOut ? 'Enable' : 'Disable'}
          </button>
        </div>
      )}
      
      {/* Stats Overview */}
      <section className="section">
        <StatsOverview stats={data.stats} />
      </section>

      {/* Default Punishment Banner */}
      <DefaultPunishmentBanner 
        value={data.user.default_punishment} 
        discordId={discordId} 
        appUserId={appUserId} 
        addToast={addToast}
        onSaved={(val) => { if (data) data.user.default_punishment = val; }}
      />

      {/* Science-backed motivation link */}
      <a
        href="/fc/motivation.html"
        target="_blank"
        rel="noopener noreferrer"
        style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          padding: '10px 16px', marginBottom: '12px',
          background: 'linear-gradient(135deg, rgba(59,130,246,0.08), rgba(168,85,247,0.08))',
          border: '1px solid rgba(59,130,246,0.15)', borderRadius: '10px',
          color: '#94a3b8', fontSize: '0.82rem', textDecoration: 'none',
          transition: 'border-color 0.2s',
        }}
        onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(59,130,246,0.4)')}
        onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(59,130,246,0.15)')}
      >
        <span style={{ fontSize: '1.1rem' }}>🧠</span>
        <span><strong style={{ color: '#f1f5f9' }}>The Science of Showing Up</strong> — 10 research-backed techniques for motivation &amp; consistency</span>
        <span style={{ marginLeft: 'auto', color: '#3b82f6', fontWeight: 600, flexShrink: 0 }}>&rarr;</span>
      </a>

      {/* Inline setup form (toggle) */}
      {showSetupForm && appUserId && (
        <section className="section">
          <TaskSetupForm appUserId={appUserId} onTaskCreated={() => { setShowSetupForm(false); fetchDashboard(); }} />
        </section>
      )}
      
      {/* Tabs */}
      <div className="tabs">
        <button className={`tab ${activeTab === 'tasks' ? 'active' : ''}`} onClick={() => setActiveTab('tasks')}>
          📋 Tasks
        </button>
        <button className={`tab ${activeTab === 'goals' ? 'active' : ''}`} onClick={() => setActiveTab('goals')}>
          🏆 Goals
        </button>
        <button className={`tab ${activeTab === 'score' ? 'active' : ''}`} onClick={() => setActiveTab('score')}>
          📊 Score
        </button>
        <button className={`tab ${activeTab === 'insights' ? 'active' : ''}`} onClick={() => setActiveTab('insights')}>
          🧠 Insights
        </button>
        <button className={`tab ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>
          📜 History
        </button>
      </div>
      
      {/* Tasks Tab */}
      {activeTab === 'tasks' && (
        <section className="section">
          <h2>Active Tasks</h2>
          {data.tasks.length === 0 ? (
            <div className="empty-state">
              <p>No active tasks yet.</p>
              {appUserId ? (
                <button
                  onClick={() => setShowSetupForm(true)}
                  style={{
                    marginTop: '0.5rem', padding: '0.5rem 1rem', borderRadius: '0.5rem',
                    background: '#8b5cf6', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 600
                  }}
                >
                  Create Your First Task
                </button>
              ) : (
                <p>Use <code>/fc-coach setup taskname:gym</code> in Discord to get started!</p>
              )}
            </div>
          ) : (
            <div className="tasks-grid">
              {data.tasks.map((task) => (
                <TaskCard 
                  key={task.id} 
                  task={task} 
                  onCheckin={handleCheckin}
                  onRefresh={fetchDashboard}
                  isLoading={checkinLoading === task.id}
                  discordId={discordId}
                  appUserId={appUserId}
                  addToast={addToast}
                  defaultPunishment={data.user.default_punishment}
                />
              ))}
            </div>
          )}
        </section>
      )}
      
      {/* Goals Tab */}
      {activeTab === 'goals' && (
        <section className="section">
          <h2>Super Goals</h2>
          <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '20px', lineHeight: 1.5 }}>
            Combine multiple tasks into a Super Goal and track your estimated probability of success.
            The more consistently you complete your linked tasks, the higher your odds climb.
          </p>

          {superGoals.length === 0 && (
            <div className="super-goals-empty">
              <h3>No Super Goals yet</h3>
              <p>Link your tasks together into a bigger goal and see your estimated probability of achieving it.</p>
              <div className="example-text">
                <strong style={{ color: '#a78bfa' }}>Example:</strong> "Get Healthier" — Link <em>Gym</em> (35%), <em>Eat Meals</em> (25%),
                <em> Sleep Schedule</em> (20%), <em>Drink Water</em> (10%), and <em>Get Sunlight</em> (10%).
                As you check in daily, watch your probability climb!
              </div>
            </div>
          )}

          {superGoals.length > 0 && data && (
            <div className="super-goals-grid">
              {superGoals.map(goal => (
                <SuperGoalCard
                  key={goal.id}
                  goal={goal}
                  tasks={data.tasks}
                  onEdit={(g) => { setEditingSuperGoal(g); setShowSuperGoalForm(true); }}
                  onDelete={handleDeleteSuperGoal}
                />
              ))}
            </div>
          )}

          {data && data.tasks.filter(t => !t.is_paused).length >= 2 && (
            <div style={{ marginTop: '20px' }}>
              <button className="create-super-goal-btn" onClick={() => { setEditingSuperGoal(null); setShowSuperGoalForm(true); }}>
                ➕ Create Super Goal
              </button>
            </div>
          )}

          {data && data.tasks.filter(t => !t.is_paused).length < 2 && (
            <p style={{ fontSize: '0.82rem', color: '#64748b', marginTop: '16px', textAlign: 'center' }}>
              You need at least 2 active tasks to create a Super Goal.
              <button
                onClick={() => setShowSetupForm(true)}
                style={{ color: '#a78bfa', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600, textDecoration: 'underline', marginLeft: '4px' }}
              >
                Add a task
              </button>
            </p>
          )}
        </section>
      )}

      {/* Super Goal Form Modal */}
      {showSuperGoalForm && data && (
        <SuperGoalForm
          tasks={data.tasks}
          existingGoal={editingSuperGoal}
          onSave={handleSuperGoalSaved}
          onCancel={() => { setShowSuperGoalForm(false); setEditingSuperGoal(null); }}
          discordId={discordId}
          appUserId={appUserId}
        />
      )}

      {/* Score Tab */}
      {activeTab === 'score' && (
        <section className="section">
          <h2>Accountability Score</h2>
          <ScorePanel discordId={discordId} appUserId={appUserId} />
        </section>
      )}

      {/* Insights Tab */}
      {activeTab === 'insights' && (
        <section className="section">
          {/* ── Pattern Finder ── */}
          <div className="subsection">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h2 style={{ margin: 0 }}>🔍 Pattern Finder</h2>
              <button
                className="pf-refresh-btn"
                onClick={handleDetectPatterns}
                disabled={patternsLoading}
              >
                {patternsLoading ? '⏳ Analyzing...' : '🔄 Refresh Patterns'}
              </button>
            </div>
            <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '16px', lineHeight: 1.5 }}>
              Automatically finds correlations between your tasks — which habits reinforce each other?
              Patterns are detected from your last 60 days of check-in data.
            </p>

            {patternsLoading && detectedPatterns.length === 0 && (
              <div className="pf-loading">
                <span>⏳</span> Analyzing your check-in history for patterns...
              </div>
            )}

            {!patternsLoading && detectedPatterns.length === 0 && (
              <div className="pf-empty">
                <h3>No patterns detected yet</h3>
                <p>We need at least 2 active tasks with 7+ days of check-in history to find correlations.
                Keep checking in and we'll discover which habits reinforce each other!</p>
                <button className="pf-detect-btn" onClick={handleDetectPatterns} disabled={patternsLoading}>
                  Run Pattern Detection
                </button>
              </div>
            )}

            {detectedPatterns.filter(p => p.status === 'active').length > 0 && (
              <div className="pf-grid">
                {detectedPatterns.filter(p => p.status === 'active').map(p => (
                  <PatternCard
                    key={p.id}
                    pattern={p}
                    tasks={data.tasks}
                    onRate={handleRatePattern}
                    onDismiss={handleDismissPattern}
                  />
                ))}
              </div>
            )}

            {/* Disclaimer */}
            {detectedPatterns.filter(p => p.status === 'active').length > 0 && (
              <div className="pf-disclaimer">
                <strong>Correlation ≠ causation.</strong> These patterns show what tends to happen together in
                your data — not necessarily cause and effect. Use them as motivational signals, not medical advice.
              </div>
            )}
          </div>

          {/* ── Hypothesis testing ── */}
          {data.tasks.filter(t => !t.is_paused).length >= 2 && (
            <div className="subsection">
              <HypothesisForm
                tasks={data.tasks}
                discordId={discordId}
                appUserId={appUserId}
                onCreated={(patterns) => {
                  setDetectedPatterns(patterns);
                  addToast('Hypothesis Created', 'We checked your data for this pattern.', 'info');
                }}
              />
            </div>
          )}

          {/* ── Existing identity/behavioral sections ── */}
          {data.identities.length > 0 && (
            <div className="subsection">
              <h2>Identity Adherence</h2>
              <div className="identities-grid">
                {data.identities.map((identity) => (
                  <IdentityCard key={identity.name} identity={identity} />
                ))}
              </div>
            </div>
          )}
          {data.patterns.length > 0 && (
            <div className="subsection">
              <h2>Behavioral Insights</h2>
              <div className="patterns-list">
                {data.patterns.map((pattern, idx) => (
                  <PatternInsight key={idx} pattern={pattern} />
                ))}
              </div>
            </div>
          )}
        </section>
      )}
      
      {/* History Tab */}
      {activeTab === 'history' && (
        <section className="section">
          <h2>Recent Activity</h2>
          <RecentActivity checkins={data.recent_checkins} />
        </section>
      )}
      
      {/* Footer */}
      <footer className="dashboard-footer">
        <p>
          {authMode === 'discord' ? (
            <>Use <code>/fc-coach</code> commands in Discord for full functionality</>
          ) : (
            <>Manage your tasks from this dashboard or link Discord for bot commands</>
          )}
        </p>
        <p><a href="#/guest">← Back to FavCreators</a></p>
      </footer>
    </div>
  );
}
