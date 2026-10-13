/* ───────────────────────────────────────────────────────────────────────────
   ServiceNow JavaScript — quiz question bank
   Consumed by quiz.html. Kept as a separate file so adding questions is a
   plain append — no HTML changes, no new check functions.

   Every answer here was cross-checked against the official ServiceNow API
   references and against the corrections in ../index.html (see
   ../../../updates/2026-10-12-servicenow-js-hallucination-audit.md):
     • orderByDesc() exists, setDesc() does not
     • addDays(-3), not subtractDays(3)
     • getRowCount(), getUniqueValue(), isValidField() are real
     • GlideQueryCondition is what addQuery() returns — it has no constructor
     • addAggregate(agg, name) / getAggregate(agg, name) take the field as 2nd arg
     • getXMLWait() is unavailable to scoped apps — prefer getXMLAnswer()

   Question shape:
     id       unique string
     cat      one of the category ids below
     sub      one of that category's sub ids
     type     'code'  → user types code (default)   |  'text' → short answer
     q        the prompt
     ph       input placeholder
     accept   array of accepted forms. Compared AFTER normalisation, so
              whitespace, quote style and a trailing ';' do not matter.
     answer   the canonical form, shown on failure and in the answer key
     hint     optional nudge, revealed on request
   ─────────────────────────────────────────────────────────────────────────── */

window.SN_QUIZ = {
  version: '2026-10-12',

  categories: [
    {
      id: 'gliderecord',
      label: 'GlideRecord',
      icon: '\u{1F5C4}️',
      accent: '#62f5c7',
      blurb: 'Query tables, add conditions, iterate rows and write records back.',
      subs: [
        { id: 'query',  label: 'Querying' },
        { id: 'fields', label: 'Reading fields' },
        { id: 'crud',   label: 'Insert / update / delete' }
      ]
    },
    {
      id: 'encodedquery',
      label: 'Encoded Queries & GlideQuery',
      icon: '\u{1F50E}',
      accent: '#7aa2ff',
      blurb: 'Filter strings, condition objects and the modern fluent builder.',
      subs: [
        { id: 'strings', label: 'Filter strings' },
        { id: 'cond',    label: 'Conditions & OR logic' },
        { id: 'gq',      label: 'GlideQuery' }
      ]
    },
    {
      id: 'glideaggregate',
      label: 'GlideAggregate',
      icon: '\u{1F4CA}',
      accent: '#fbbf24',
      blurb: 'COUNT / SUM / AVG computed on the database, plus multi-column groupBy.',
      subs: [
        { id: 'basic',  label: 'Counts & sums' },
        { id: 'group',  label: 'Grouping' }
      ]
    },
    {
      id: 'glidedatetime',
      label: 'GlideDateTime',
      icon: '\u{1F552}',
      accent: '#f472b6',
      blurb: 'Server-side dates and timezones — never native JS Date.',
      subs: [
        { id: 'basic',   label: 'Create & read' },
        { id: 'arith',   label: 'Arithmetic' },
        { id: 'compare', label: 'Compare' }
      ]
    },
    {
      id: 'glideajax',
      label: 'GlideAjax & Script Includes',
      icon: '\u{1F4E1}',
      accent: '#a78bfa',
      blurb: 'Round-trip from a client script to server code without reloading.',
      subs: [
        { id: 'client', label: 'Client side' },
        { id: 'server', label: 'Script Include side' }
      ]
    },
    {
      id: 'gform',
      label: 'g_form & Client Scripts',
      icon: '\u{1F4DD}',
      accent: '#4ade80',
      blurb: 'Drive the form: field state, messages, onChange and onSubmit.',
      subs: [
        { id: 'fields',    label: 'Field control' },
        { id: 'messages',  label: 'Messages' },
        { id: 'lifecycle', label: 'onChange / onSubmit' }
      ]
    },
    {
      id: 'glidesystem',
      label: 'GlideSystem (gs)',
      icon: '\u2699\uFE0F',
      accent: '#38bdf8',
      blurb: 'Session, roles, properties, logging and date helpers.',
      subs: [
        { id: 'session', label: 'User & roles' },
        { id: 'util',    label: 'Utilities' },
        { id: 'logging', label: 'Logging & messaging' }
      ]
    },
    {
      id: 'jsfundamentals',
      label: 'JavaScript for Interviews',
      icon: '\u{1F9E9}',
      accent: '#f59e0b',
      blurb: 'Plain JS building blocks for LeetCode-style problems: strings, Set/Map, and the frequency-count idiom.',
      subs: [
        { id: 'strings',  label: 'String methods' },
        { id: 'types',    label: 'Set / Map / Object' },
        { id: 'patterns', label: 'Counting idioms' }
      ]
    }
  ],

  questions: [

    /* ── GlideRecord ────────────────────────────────────────────────────── */
    {
      id: 'gr-01', cat: 'gliderecord', sub: 'query',
      q: 'Add a condition to <code>gr</code> so the query only returns records where <code>priority</code> is 1.',
      ph: "e.g. gr.addQuery('priority', 1)",
      accept: ["gr.addQuery('priority', 1)", "gr.addQuery('priority', '=', 1)", "gr.addQuery('priority','=','1')", "gr.addQuery('priority', '1')"],
      answer: "gr.addQuery('priority', 1)",
      hint: "addQuery() takes field, optional operator, value — the operator defaults to equals."
    },
    {
      id: 'gr-02', cat: 'gliderecord', sub: 'query',
      q: 'Restrict the query to active records only.',
      ph: "e.g. gr.addActiveQuery()",
      accept: ["gr.addActiveQuery()", "gr.addQuery('active', true)", "gr.addQuery('active', '=', true)"],
      answer: 'gr.addActiveQuery()',
      hint: "There is a dedicated shorthand for the active=true condition."
    },
    {
      id: 'gr-03', cat: 'gliderecord', sub: 'query',
      q: 'Limit results to records created in the last 7 days. Write the full condition line using an <em>evaluated</em> date.',
      ph: "e.g. gr.addQuery('sys_created_on', '>=', gs.daysAgoStart(7))",
      accept: [
        "gr.addQuery('sys_created_on', '>=', gs.daysAgoStart(7))",
        "gr.addQuery('sys_created_on', '>=',gs.daysAgoStart(7))"
      ],
      answer: "gr.addQuery('sys_created_on', '>=', gs.daysAgoStart(7))",
      hint: "gs.daysAgoStart(7) returns the internal-format date string — pass it, don't quote a javascript: literal."
    },
    {
      id: 'gr-04', cat: 'gliderecord', sub: 'query',
      q: 'Sort the result descending by <code>sys_created_on</code>.',
      ph: "e.g. gr.orderByDesc('sys_created_on')",
      accept: ["gr.orderByDesc('sys_created_on')", "orderByDesc('sys_created_on')"],
      answer: "gr.orderByDesc('sys_created_on')",
      hint: "orderByDesc — note that setDesc() does not exist on GlideRecord."
    },
    {
      id: 'gr-05', cat: 'gliderecord', sub: 'query',
      q: 'Only load 25 rows per page of the query window. Which method takes the start row and the count?',
      ph: 'e.g. gr.chooseWindow(0, 25)',
      accept: ['gr.chooseWindow(0, 25)', 'chooseWindow(0, 25)', 'gr.chooseWindow(0,25)'],
      answer: 'gr.chooseWindow(0, 25)',
      hint: 'It "chooses" a window into the result set.'
    },
    {
      id: 'gr-06', cat: 'gliderecord', sub: 'fields',
      q: 'Read the <code>short_description</code> of the row the cursor is currently on.',
      ph: "e.g. gr.getValue('short_description')",
      accept: ["gr.getValue('short_description')", "getValue('short_description')", 'gr.short_description'],
      answer: "gr.getValue('short_description')",
      hint: "getValue() is the safe reader — it returns null for empty rather than undefined."
    },
    {
      id: 'gr-07', cat: 'gliderecord', sub: 'fields',
      q: 'Get the <code>sys_id</code> of the current row.',
      ph: 'e.g. gr.getUniqueValue()',
      accept: ['gr.getUniqueValue()'],
      answer: 'gr.getUniqueValue()',
      hint: "It's the table's unique value — not getID()."
    },
    {
      id: 'gr-08', cat: 'gliderecord', sub: 'fields',
      q: 'Before reading <code>u_custom_field</code>, confirm the table actually has that column. Which method returns a boolean?',
      ph: "e.g. gr.isValidField('u_custom_field')",
      accept: ["gr.isValidField('u_custom_field')", "isValidField('u_custom_field')"],
      answer: "gr.isValidField('u_custom_field')",
      hint: "Field, not record — the name says exactly what it checks."
    },
    {
      id: 'gr-09', cat: 'gliderecord', sub: 'crud',
      q: 'Insert a brand-new incident with short description "Scripted insert". Write the two lines that initialise and set the field.',
      ph: 'e.g. gr.initialize() / gr.short_description = ...',
      accept: ["gr.initialize(); gr.short_description = 'Scripted insert';", "gr.initialize() gr.short_description = 'Scripted insert'"],
      answer: "gr.initialize(); gr.short_description = 'Scripted insert';",
      hint: "initialize() resets the GlideRecord so a bare assignment becomes a new row rather than an edit."
    },
    {
      id: 'gr-10', cat: 'gliderecord', sub: 'crud',
      q: 'After changing fields on the current row, write the line that saves it back to the database.',
      ph: 'e.g. gr.update()',
      accept: ['gr.update()'],
      answer: 'gr.update()',
      hint: "Nothing is written until you ask."
    },
    {
      id: 'gr-11', cat: 'gliderecord', sub: 'crud',
      q: 'Hard-delete the row the cursor is on.',
      ph: 'e.g. gr.deleteRecord()',
      accept: ['gr.deleteRecord()'],
      answer: 'gr.deleteRecord()',
      hint: "deleteRecord, not remove()."
    },

    /* ── Encoded queries & GlideQuery ───────────────────────────────────── */
    {
      id: 'eq-01', cat: 'encodedquery', sub: 'strings',
      q: 'Apply a pre-built filter string to <code>gr</code>: active incidents with priority 1.',
      ph: "e.g. gr.addEncodedQuery('active=true^priority=1')",
      accept: ["gr.addEncodedQuery('active=true^priority=1')", "addEncodedQuery('active=true^priority=1')"],
      answer: "gr.addEncodedQuery('active=true^priority=1')",
      hint: 'Caret ^ is the AND separator in a filter string.'
    },
    {
      id: 'eq-02', cat: 'encodedquery', sub: 'strings',
      q: 'Write the encoded-query clause that matches every record whose <code>assigned_to</code> is empty.',
      ph: 'e.g. assigned_toISEMPTY',
      accept: ['assigned_toISEMPTY', 'assigned_to ISEMPTY'],
      answer: 'assigned_toISEMPTY',
      hint: 'No operator symbol — the keyword is jammed against the field name.'
    },
    {
      id: 'eq-03', cat: 'encodedquery', sub: 'strings',
      q: 'Write the encoded-query clause for "priority is 1 or 2".',
      ph: 'e.g. priorityIN1,2',
      accept: ['priorityIN1,2', 'priority IN1,2', 'priorityIN1, 2'],
      answer: 'priorityIN1,2',
      hint: 'IN takes a comma-separated list with no spaces.'
    },
    {
      id: 'eq-04', cat: 'encodedquery', sub: 'strings',
      q: 'Retrieve the filter string that represents everything <code>gr</code> is currently querying.',
      ph: 'e.g. gr.getEncodedQuery()',
      accept: ['gr.getEncodedQuery()'],
      answer: 'gr.getEncodedQuery()',
      hint: 'The getter has the same name as the setter.'
    },
    {
      id: 'eq-05', cat: 'encodedquery', sub: 'cond',
      q: '<code>addQuery()</code> hands back an object. What method on that object adds an OR condition instead of a new AND row?',
      ph: "e.g. addOrCondition('priority', 2)",
      accept: ["addOrCondition('priority', 2)", "addOrCondition()", "c.addOrCondition('priority', 2)", "gr.addOrCondition('priority', 2)", "addOrCondition('priority',2)"],
      answer: "addOrCondition('priority', 2)",
      hint: 'It is a GlideQueryCondition — returned by addQuery(), never constructed with new.'
    },
    {
      id: 'eq-06', cat: 'encodedquery', sub: 'cond',
      q: 'Add a condition that <code>assigned_to</code> is empty, using the dedicated GlideRecord shorthand.',
      ph: "e.g. gr.addNullQuery('assigned_to')",
      accept: ["gr.addNullQuery('assigned_to')", "gr.addNullQuery('assigned_to')", "addNullQuery('assigned_to')"],
      answer: "gr.addNullQuery('assigned_to')",
      hint: 'Null query — the field has no value.'
    },
    {
      id: 'eq-07', cat: 'encodedquery', sub: 'gq',
      q: 'Name the modern fluent query-builder API that returns records directly, instead of assembling a string by hand.',
      ph: 'e.g. GlideQuery',
      accept: ['GlideQuery', 'glidequery', 'new GlideQuery()'],
      answer: 'GlideQuery',
      hint: 'Different from GlideQueryCondition, which is only the condition object addQuery() returns.'
    },
    {
      id: 'eq-08', cat: 'encodedquery', sub: 'gq',
      q: 'Complete the GlideQuery chain: match active P1 incidents, cap the result at 50 rows.',
      ph: ".where('active', true).limit(50)",
      accept: [".where('active', true).limit(50)", "where('active', true).limit(50)", ".limit(50)"],
      answer: ".where('active', true).limit(50)",
      hint: 'where() adds the condition, limit() caps the rows.'
    },

    /* ── GlideAggregate ─────────────────────────────────────────────────── */
    {
      id: 'ga-01', cat: 'glideaggregate', sub: 'basic',
      q: 'Create an aggregate query against the <code>incident</code> table.',
      ph: "e.g. new GlideAggregate('incident')",
      accept: ["new GlideAggregate('incident')", 'new GlideAggregate("incident")', "new GlideAggregate ( 'incident' )"],
      answer: "new GlideAggregate('incident')",
      hint: 'Same constructor shape as GlideRecord, different class.'
    },
    {
      id: 'ga-02', cat: 'glideaggregate', sub: 'basic',
      q: 'Declare a plain row count on <code>agg</code> (no field name needed).',
      ph: "e.g. agg.addAggregate('COUNT')",
      accept: ["agg.addAggregate('COUNT')", "addAggregate('COUNT')", "agg.addAggregate('COUNT', 'priority')"],
      answer: "agg.addAggregate('COUNT')",
      hint: 'COUNT without a field counts rows; COUNT with a field counts that field\'s non-null values.'
    },
    {
      id: 'ga-03', cat: 'glideaggregate', sub: 'basic',
      q: 'Add an average of the <code>assignment_time</code> field. Remember the aggregate name and the field are separate arguments.',
      ph: "e.g. agg.addAggregate('AVG', 'assignment_time')",
      accept: ["agg.addAggregate('AVG', 'assignment_time')", "agg.addAggregate('AVG','assignment_time')", "addAggregate('AVG', 'assignment_time')"],
      answer: "agg.addAggregate('AVG', 'assignment_time')",
      hint: 'addAggregate(agg, name).'
    },
    {
      id: 'ga-04', cat: 'glideaggregate', sub: 'basic',
      q: 'Inside the loop, read the count you declared with <code>addAggregate(\'COUNT\')</code>.',
      ph: "e.g. agg.getAggregate('COUNT')",
      accept: ["agg.getAggregate('COUNT')", "getAggregate('COUNT')", "agg.getAggregate('COUNT', 'priority')"],
      answer: "agg.getAggregate('COUNT')",
      hint: 'The read must name the same aggregate (and field) you declared.'
    },
    {
      id: 'ga-05', cat: 'glideaggregate', sub: 'group',
      q: 'Group the aggregate by <code>priority</code>.',
      ph: "e.g. agg.groupBy('priority')",
      accept: ["agg.groupBy('priority')", "agg.addGroupBy('priority')", "groupBy('priority')"],
      answer: "agg.groupBy('priority')",
      hint: 'addGroupBy() is the older alias for the same thing.'
    },
    {
      id: 'ga-06', cat: 'glideaggregate', sub: 'group',
      q: 'Add a <em>second</em> grouping column, <code>category</code>, so the result has one row per priority+category pair.',
      ph: "e.g. agg.groupBy('category')",
      accept: ["agg.groupBy('category')", "agg.addGroupBy('category')", "groupBy('category')"],
      answer: "agg.groupBy('category')",
      hint: 'Call groupBy() again — one call per column.'
    },
    {
      id: 'ga-07', cat: 'glideaggregate', sub: 'basic',
      q: 'Order the aggregate results by the computed count, highest first. Give the two-argument form.',
      ph: "e.g. agg.orderByAggregate('COUNT', 'priority')",
      accept: ["agg.orderByAggregate('COUNT', 'priority')", "agg.orderByAggregate('COUNT','priority')", "orderByAggregate('COUNT', 'priority')"],
      answer: "agg.orderByAggregate('COUNT', 'priority')",
      hint: 'orderByAggregate(agg, name) - and setDesc() does not exist, use orderByDesc().'
    },
    {
      id: 'ga-08', cat: 'glideaggregate', sub: 'basic',
      q: 'You want <em>one overall</em> average across a filtered slice, not a row per group. Which documented method collapses the result to a single row?',
      ph: 'e.g. agg.setGroup(false)',
      accept: ['agg.setGroup(false)', 'agg.setGroup(0)', 'setGroup(false)'],
      answer: 'agg.setGroup(false)',
      hint: 'With no groupBy() you already get one row; this is the explicit insurance, and the idiomatic write alongside addHaving().'
    },
    {
      id: 'ga-09', cat: 'glideaggregate', sub: 'basic',
      q: '<code>getAggregate()</code> hands back a <em>string</em>. What do you wrap it in before doing arithmetic on it?',
      ph: "e.g. parseFloat(agg.getAggregate('AVG', 'sys_mod_count'))",
      accept: ["parseFloat(agg.getAggregate('AVG', 'sys_mod_count'))", 'parseFloat(...)', 'parseFloat()'],
      answer: "parseFloat(agg.getAggregate('AVG', 'sys_mod_count'))",
      hint: 'Otherwise adding two of them concatenates the strings instead of summing.'
    },
    {
      id: 'ga-10', cat: 'glideaggregate', sub: 'group',
      q: 'Name the documented companion to <code>setGroup()</code> that turns result <em>sorting</em> off.',
      ph: 'e.g. agg.setOrder(false)',
      accept: ['agg.setOrder(false)', 'setOrder(false)', 'agg.setOrder(0)'],
      answer: 'agg.setOrder(false)',
      hint: 'Same shape as setGroup - one boolean, off by default.'
    },

    /* ── GlideDateTime ──────────────────────────────────────────────────── */
    {
      id: 'dt-01', cat: 'glidedatetime', sub: 'basic',
      q: 'Create a GlideDateTime holding the current moment.',
      ph: 'e.g. new GlideDateTime()',
      accept: ['new GlideDateTime()', 'new GlideDateTime( )'],
      answer: 'new GlideDateTime()',
      hint: 'No argument means "now".'
    },
    {
      id: 'dt-02', cat: 'glidedatetime', sub: 'basic',
      q: 'Get the stored value of <code>gdt</code> as the internal string <code>yyyy-MM-dd HH:mm:ss</code>.',
      ph: 'e.g. gdt.getValue()',
      accept: ['gdt.getValue()'],
      answer: 'gdt.getValue()',
      hint: 'getValue is the raw/internal reader.'
    },
    {
      id: 'dt-03', cat: 'glidedatetime', sub: 'basic',
      q: 'Get <code>gdt</code> rendered in the <em>current user\'s</em> format and timezone.',
      ph: 'e.g. gdt.getDisplayValue()',
      accept: ['gdt.getDisplayValue()'],
      answer: 'gdt.getDisplayValue()',
      hint: 'The user-facing reader. getDisplayValueInternal() keeps the user\'s timezone but switches to the system format.'
    },
    {
      id: 'dt-04', cat: 'glidedatetime', sub: 'arith',
      q: 'Move <code>gdt</code> back exactly 3 days. There is no subtractDays — write the real call.',
      ph: 'e.g. gdt.addDays(-3)',
      accept: ['gdt.addDays(-3)', 'gdt.addDays( -3 )'],
      answer: 'gdt.addDays(-3)',
      hint: 'Negate the argument.'
    },
    {
      id: 'dt-05', cat: 'glidedatetime', sub: 'arith',
      q: 'Advance <code>gdt</code> by one hour in seconds.',
      ph: 'e.g. gdt.addSeconds(3600)',
      accept: ['gdt.addSeconds(3600)'],
      answer: 'gdt.addSeconds(3600)',
      hint: 'addSeconds takes the delta in seconds.'
    },
    {
      id: 'dt-06', cat: 'glidedatetime', sub: 'arith',
      q: 'Shift <code>gdt</code> by 2 days using <em>local</em> time rather than UTC.',
      ph: 'e.g. gdt.addDaysLocalTime(-2)',
      accept: ['gdt.addDaysLocalTime(-2)', 'gdt.addDaysLocalTime(2)'],
      answer: 'gdt.addDaysLocalTime(-2)',
      hint: 'The LocalTime variants exist for days and months.'
    },
    {
      id: 'dt-07', cat: 'glidedatetime', sub: 'compare',
      q: 'Return true when <code>gdt1</code> is strictly earlier than <code>gdt2</code>. Do not compare the objects with &lt;.',
      ph: 'e.g. gdt1.before(gdt2)',
      accept: ['gdt1.before(gdt2)', 'gdt1.before(gdt2);', 'gdt.before(other)'],
      answer: 'gdt1.before(gdt2)',
      hint: 'before() / after() / equals() are the documented comparison methods.'
    },
    {
      id: 'dt-08', cat: 'glidedatetime', sub: 'basic',
      q: 'What integer does <code>getDayOfWeek()</code> return for Sunday?',
      ph: 'e.g. 7',
      accept: ['7'],
      answer: '7',
      hint: 'The week starts on Monday: 1 = Monday … 7 = Sunday.'
    },

    /* ── GlideAjax ──────────────────────────────────────────────────────── */
    {
      id: 'aj-01', cat: 'glideajax', sub: 'client',
      q: 'Create a GlideAjax call targeting the Script Include named <code>MyAjaxUtils</code>.',
      ph: "e.g. new GlideAjax('MyAjaxUtils')",
      accept: ["new GlideAjax('MyAjaxUtils')", 'new GlideAjax("MyAjaxUtils")'],
      answer: "new GlideAjax('MyAjaxUtils')",
      hint: 'The string is the Script Include\'s type name, not its file name.'
    },
    {
      id: 'aj-02', cat: 'glideajax', sub: 'client',
      q: 'Tell GlideAjax which server-side method to run. The parameter name is fixed by the platform.',
      ph: "e.g. ga.addParam('sysparm_name', 'getCallerInfo')",
      accept: ["ga.addParam('sysparm_name', 'getCallerInfo')", "ga.addParam('sysparm_name','getCallerInfo')"],
      answer: "ga.addParam('sysparm_name', 'getCallerInfo')",
      hint: "sysparm_name is the magic key."
    },
    {
      id: 'aj-03', cat: 'glideajax', sub: 'client',
      q: 'Client-script context: you are writing an <code>onChange</code> client script on the <code>caller_id</code> field and fire GlideAjax from inside its handler. Pass the field\'s new value (the caller\'s sys_id) as a parameter named <code>sysparm_caller_id</code>.',
      ph: "e.g. ga.addParam('sysparm_caller_id', newValue)",
      accept: ["ga.addParam('sysparm_caller_id', newValue)", "ga.addParam('sysparm_caller_id',g_form.getValue('caller_id'))", "ga.addParam('sysparm_caller_id', g_form.getValue('caller_id'))"],
      answer: "ga.addParam('sysparm_caller_id', newValue)",
      hint: 'Every custom parameter must start with sysparm_. In an onChange handler the 4th-argument newValue already holds the new sys_id (reference fields pass the sys_id, not the display value) — that is why the canonical answer uses it. In any other client context (onLoad, onSubmit, UI Action) there is no newValue, so use g_form.getValue(\'caller_id\') instead — both forms are accepted here.'
    },
    {
      id: 'aj-04', cat: 'glideajax', sub: 'client',
      q: 'Fire the call and handle the reply asynchronously, reading the <code>answer</code> string. Give the method name.',
      ph: 'e.g. ga.getXMLAnswer(function(answer){ ... })',
      accept: ['ga.getXMLAnswer(function(answer){ ... })', 'getXMLAnswer', 'ga.getXMLAnswer(cb)', 'ga.getXMLAnswer(function(answer) {})'],
      answer: 'ga.getXMLAnswer(function(answer){ ... })',
      hint: 'getXMLAnswer hands the callback a plain string.'
    },
    {
      id: 'aj-05', cat: 'glideajax', sub: 'client',
      q: 'Name the synchronous GlideAjax method that blocks the UI thread — and is unavailable to scoped applications and Service Portal.',
      ph: 'e.g. ga.getXMLWait()',
      accept: ['ga.getXMLWait()', 'getXMLWait', 'getXMLWait()'],
      answer: 'ga.getXMLWait()',
      hint: 'The "Wait" in the name is the problem, not a feature.'
    },
    {
      id: 'aj-06', cat: 'glideajax', sub: 'server',
      q: 'In the Script Include, which property declares the name the client passes to <code>new GlideAjax(...)</code>?',
      ph: "e.g. type: 'MyAjaxUtils'",
      accept: ["type: 'MyAjaxUtils'", "type:'MyAjaxUtils'", 'type'],
      answer: "type: 'MyAjaxUtils'",
      hint: 'It sits alongside the function definitions at the bottom of the IIFE.'
    },
    {
      id: 'aj-07', cat: 'glideajax', sub: 'server',
      q: 'Which Script Include flag must be enabled before a client script can call it with GlideAjax?',
      ph: 'e.g. Client callable',
      accept: ['Client callable', 'client callable', 'Client Callable', 'clientCallable', 'client_callable'],
      answer: 'Client callable',
      hint: 'It is the "Client callable" checkbox (field client_callable, under the Client section of the Script Include form) — not a line of code. Often misremembered as an "ajax enabled" box; no such flag exists. Without it, GlideAjax cannot see the Script Include at all.'
    },
    {
      id: 'aj-08', cat: 'glideajax', sub: 'client',
      q: 'After <code>getXMLWait()</code>, how do you read the returned value?',
      ph: 'e.g. ga.getAnswer()',
      accept: ['ga.getAnswer()'],
      answer: 'ga.getAnswer()',
      hint: 'The synchronous counterpart of the async callback.'
    },
    {
      id: 'aj-09', cat: 'glideajax', sub: 'client',
      q: 'Wire the full-response method: fire <code>ga.getXML()</code> with a callback, then read the <code>answer</code> attribute out of <code>response.responseXML.documentElement</code>. Give the complete wiring (setup lines such as <code>new GlideAjax(\'...\')</code> are optional).',
      ph: "e.g. ga.getXML(answerFunction); function answerFunction(response) { var answer = response.responseXML.documentElement.getAttribute('answer'); }",
      accept: [
        "ga.getXML(answerFunction); function answerFunction(response) { var answer = response.responseXML.documentElement.getAttribute('answer'); }",
        "ga.getXML(answerFunction); function answerFunction(response) { var answer = response.responseXML.documentElement.getAttribute(\"answer\"); }",
        "ga.getXML(cb); function cb(response) { var answer = response.responseXML.documentElement.getAttribute('answer'); }",
        "ga.getXML(cb); function cb(response) { var answer = response.responseXML.documentElement.getAttribute(\"answer\"); }",
        "ga.getXML(function(response) { var answer = response.responseXML.documentElement.getAttribute('answer'); });",
        "ga.getXML(function(response) { var answer = response.responseXML.documentElement.getAttribute(\"answer\"); });",
        "var ga = new GlideAjax('YourScriptInclude'); ga.addParam('sysparm_name', 'yourFunction'); ga.getXML(answerFunction); function answerFunction(response) { var answer = response.responseXML.documentElement.getAttribute(\"answer\"); }",
        "var ga = new GlideAjax('YourScriptInclude'); ga.addParam('sysparm_name', 'yourFunction'); ga.getXML(answerFunction); function answerFunction(response) { var answer = response.responseXML.documentElement.getAttribute('answer'); }"
      ],
      answer: "ga.getXML(answerFunction); function answerFunction(response) { var answer = response.responseXML.documentElement.getAttribute('answer'); }",
      hint: 'getXML hands the callback the FULL XML response, not a string — the answer sits on documentElement as an attribute, so you read it with getAttribute(\'answer\'). (getXMLAnswer, covered earlier, hands you the plain string directly.)'
    },

    /* ── g_form & client scripts ────────────────────────────────────────── */
    {
      id: 'gf-01', cat: 'gform', sub: 'fields',
      q: 'Make the <code>description</code> field mandatory on the form.',
      ph: "e.g. g_form.setMandatory('description', true)",
      accept: ["g_form.setMandatory('description', true)", "g_form.setMandatory('description',true)", "g_form.setMandatory('description', 1)"],
      answer: "g_form.setMandatory('description', true)",
      hint: 'setMandatory(field, boolean).'
    },
    {
      id: 'gf-02', cat: 'gform', sub: 'fields',
      q: 'Hide the <code>comments</code> field from the form.',
      ph: "e.g. g_form.setVisible('comments', false)",
      accept: ["g_form.setVisible('comments', false)", "g_form.setVisible('comments',false)"],
      answer: "g_form.setVisible('comments', false)",
      hint: 'setVisible, not hide().'
    },
    {
      id: 'gf-03', cat: 'gform', sub: 'fields',
      q: 'Make the <code>priority</code> field read-only for this form.',
      ph: "e.g. g_form.setReadOnly('priority', true)",
      accept: ["g_form.setReadOnly('priority', true)", "g_form.setReadOnly('priority',true)"],
      answer: "g_form.setReadOnly('priority', true)",
      hint: 'Same shape as setMandatory.'
    },
    {
      id: 'gf-04', cat: 'gform', sub: 'messages',
      q: 'Show a field-level <em>error</em> message against <code>caller_id</code>.',
      ph: "e.g. g_form.showFieldMsg('caller_id', 'Not a VIP', 'error')",
      accept: ["g_form.showFieldMsg('caller_id', 'Not a VIP', 'error')", "g_form.showFieldMsg('caller_id', info.error, 'error')", "g_form.showFieldMsg('caller_id', msg, 'error')"],
      answer: "g_form.showFieldMsg('caller_id', 'Not a VIP', 'error')",
      hint: "Valid types are 'info', 'error' and 'warning'."
    },
    {
      id: 'gf-05', cat: 'gform', sub: 'messages',
      q: 'Clear any existing field message on <code>caller_id</code> before showing a new one, so messages do not stack.',
      ph: "e.g. g_form.hideFieldMsg('caller_id')",
      accept: ["g_form.hideFieldMsg('caller_id')", "g_form.hideFieldMsg('caller_id', true)", "hideFieldMsg('caller_id')"],
      answer: "g_form.hideFieldMsg('caller_id')",
      hint: 'hideFieldMsg(field, clearAll) — pass true to also clear server-supplied messages.'
    },
    {
      id: 'gf-06', cat: 'gform', sub: 'messages',
      q: 'Show a message across the whole form (not tied to one field).',
      ph: "e.g. g_form.addInfoMessage('VIP caller')",
      accept: ["g_form.addInfoMessage('VIP caller')", 'g_form.addInfoMessage(msg)', "g_form.addErrorMessage('Failed')", 'g_form.addErrorMessage(msg)'],
      answer: "g_form.addInfoMessage('VIP caller')",
      hint: 'addInfoMessage / addErrorMessage for form-level; showFieldMsg for one field.'
    },
    {
      id: 'gf-07', cat: 'gform', sub: 'lifecycle',
      q: 'In an <code>onSubmit</code> client script, what do you return to cancel the save?',
      ph: 'e.g. return false',
      accept: ['return false', 'false'],
      answer: 'return false',
      hint: 'Returning true (or nothing) lets the submission continue.'
    },
    {
      id: 'gf-08', cat: 'gform', sub: 'lifecycle',
      q: 'In an <code>onChange</code> script, which argument tells you this is the initial page load rather than a real user change?',
      ph: 'e.g. isLoading',
      accept: ['isLoading', 'isLoading === true', 'isLoading == true'],
      answer: 'isLoading',
      hint: 'The signature is (control, oldValue, newValue, isLoading).'
    },
    {
      id: 'gf-09', cat: 'gform', sub: 'fields',
      q: 'Read the <em>label</em> of the currently selected choice on <code>priority</code> (e.g. "2 - High"), not its value.',
      ph: "e.g. g_form.getDisplayValue('priority')",
      accept: ["g_form.getDisplayValue('priority')", "g_form.getSelectedOption('priority').getLabel()"],
      answer: "g_form.getDisplayValue('priority')",
      hint: 'getDisplayValue gives the label; getSelectedOption(...).getLabel() is the more explicit route.'
    },
    {
      id: 'gf-10', cat: 'gform', sub: 'lifecycle',
      q: 'After an async validation succeeds inside <code>onSubmit</code>, re-trigger the save using the action the user originally chose.',
      ph: 'e.g. g_form.submit(g_form.getActionName())',
      accept: ['g_form.submit(g_form.getActionName())', "g_form.submit('update')"],
      answer: 'g_form.submit(g_form.getActionName())',
      hint: 'The first submit must have returned false, or you get an infinite loop.'
    },

    /* ── GlideSystem ────────────────────────────────────────────────────── */
    {
      id: 'gs-01', cat: 'glidesystem', sub: 'session',
      q: 'Get the sys_id of the currently logged-in user.',
      ph: 'e.g. gs.getUserID()',
      accept: ['gs.getUserID()'],
      answer: 'gs.getUserID()',
      hint: 'getUserName() gives the username instead.'
    },
    {
      id: 'gs-02', cat: 'glidesystem', sub: 'session',
      q: 'Check whether the current user has the <code>admin</code> role.',
      ph: "e.g. gs.hasRole('admin')",
      accept: ["gs.hasRole('admin')", "gs.hasRole('admin');"],
      answer: "gs.hasRole('admin')",
      hint: 'One role per call.'
    },
    {
      id: 'gs-03', cat: 'glidesystem', sub: 'session',
      q: 'Client-side equivalent: check whether the browser user has <em>any</em> of a comma-separated list of roles.',
      ph: "e.g. g_user.hasRoleFromList('itil,incident_manager')",
      accept: ["g_user.hasRoleFromList('itil,incident_manager')", "g_user.hasRoleFromList('itil,incident_manager');", "g_user.hasRoleFromList('itil, incident_manager')"],
      answer: "g_user.hasRoleFromList('itil,incident_manager')",
      hint: 'hasRoles() takes a boolean, not role names.'
    },
    {
      id: 'gs-04', cat: 'glidesystem', sub: 'util',
      q: 'Check whether a value is empty/null/undefined using the platform helper.',
      ph: 'e.g. gs.nil(value)',
      accept: ['gs.nil(value)', 'gs.nil(x)', 'gs.nil(gr.field)', 'gs.nil(thisValue)'],
      answer: 'gs.nil(value)',
      hint: 'One word, one argument.'
    },
    {
      id: 'gs-05', cat: 'glidesystem', sub: 'util',
      q: 'Read a system property named <code>my.company.prop</code>.',
      ph: "e.g. gs.getProperty('my.company.prop')",
      accept: ["gs.getProperty('my.company.prop')", "gs.getProperty('my.company.prop', 'default')"],
      answer: "gs.getProperty('my.company.prop')",
      hint: 'Optional second argument supplies a default.'
    },
    {
      id: 'gs-06', cat: 'glidesystem', sub: 'util',
      q: 'Fire a named event from a business rule so another rule listening on that event runs.',
      ph: "e.g. gs.eventQueue('incident.assigned', gr)",
      accept: ["gs.eventQueue('incident.assigned', gr)", "gs.eventQueue('incident.assigned',current)", "gs.eventQueue('incident.assigned', current)"],
      answer: "gs.eventQueue('incident.assigned', gr)",
      hint: 'The second argument is the record the event carries.'
    },
    {
      id: 'gs-07', cat: 'glidesystem', sub: 'util',
      q: 'Get a GlideDateTime for the very start of today.',
      ph: 'e.g. gs.beginningOfToday()',
      accept: ['gs.beginningOfToday()'],
      answer: 'gs.beginningOfToday()',
      hint: 'endOfToday() is its pair.'
    },
    {
      id: 'gs-08', cat: 'glidesystem', sub: 'logging',
      q: 'Write a server log line at info level, substituting two arguments into <code>{0}</code> and <code>{1}</code>.',
      ph: "e.g. gs.info('P{0}: {1}', priority, summary)",
      accept: ["gs.info('P{0}: {1}', priority, summary)", "gs.info('msg {0}', arg)", 'gs.info(msg)', "gs.info('P{0}: {1}',priority,summary)"],
      answer: "gs.info('P{0}: {1}', priority, summary)",
      hint: "{0}/{1} is the ServiceNow placeholder convention — ${0} in a template literal means the number 0 instead."
    },
    {
      id: 'gs-09', cat: 'glidesystem', sub: 'logging',
      q: 'Surface a message on the user\'s form from a server-side script.',
      ph: "e.g. gs.addInfoMessage('3 incidents updated')",
      accept: ["gs.addInfoMessage('3 incidents updated')", 'gs.addInfoMessage(msg)', "gs.addErrorMessage('Failed')", 'gs.addErrorMessage(msg)'],
      answer: "gs.addInfoMessage('3 incidents updated')",
      hint: 'Note the gs. prefix — on the client the same name lives on g_form.'
    },
    {
      id: 'gs-10', cat: 'glidesystem', sub: 'util',
      q: 'Generate a new unique identifier string.',
      ph: 'e.g. gs.generateGUID()',
      accept: ['gs.generateGUID()'],
      answer: 'gs.generateGUID()',
      hint: 'GUID, not UUID.'
    },
    /* ── JavaScript for coding interviews: string methods ───────────────── */
    {
      id: 'js-01', cat: 'jsfundamentals', sub: 'strings',
      q: 'Get the <strong>last</strong> character of <code>s</code> without writing <code>s[s.length - 1]</code>. Which method accepts a negative index (ES2022)?',
      ph: 'e.g. s.at(-1)',
      accept: ['s.at(-1)', 'str.at(-1)', 's.at( -1 )'],
      answer: 's.at(-1)',
      hint: 'Same idea as Array.prototype.at().'
    },
    {
      id: 'js-02', cat: 'jsfundamentals', sub: 'strings',
      q: 'Read the character at index 1 of <code>s</code> with plain bracket notation.',
      ph: 'e.g. s[1]',
      accept: ['s[1]', 'str[1]'],
      answer: 's[1]',
      hint: 'Bracket access and at() both return undefined when out of range — at() is really about negative indices.'
    },
    {
      id: 'js-03', cat: 'jsfundamentals', sub: 'strings',
      q: 'Extract the substring from index 1 up to <em>but not including</em> index 3. Which method, and is the end exclusive?',
      ph: 'e.g. s.slice(1, 3)',
      accept: ['s.slice(1, 3)', 's.slice(1,3)', 'str.slice(1, 3)'],
      answer: 's.slice(1, 3)',
      hint: 'slice() is non-mutating and its end index is exclusive. substring() also works but mishandles negative indices.'
    },
    {
      id: 'js-04', cat: 'jsfundamentals', sub: 'strings',
      q: 'Split the string <code>s</code> into an array of its characters.',
      ph: "e.g. s.split('')",
      accept: ["s.split('')", "str.split('')", "s.split(\"\")"],
      answer: "s.split('')",
      hint: 'An empty separator splits into individual code units — which is why it is wrong for emoji.'
    },
    {
      id: 'js-05', cat: 'jsfundamentals', sub: 'strings',
      q: 'Why the last question\'s warning: an emoji like \uD83D\uDE00 is stored as <strong>two</strong> UTF-16 code units (a surrogate pair), so <code>split(\'\')</code> returns two broken \"lone surrogate\" halves instead of one character. Which ES6 way iterates a string by <em>code point</em>, keeping each emoji whole as a single array element?',
      ph: 'e.g. [...s]',
      accept: ['[...s]', 'Array.from(s)', '[ ...s ]'],
      answer: '[...s]',
      hint: 'The spread operator (and Array.from) walk the string by code point, so the surrogate pair reassembles into one element. split(\'\') walks it by code unit — that is the whole difference.\n\nRunnable (plain ASCII):\n\nx = "abcdeefghijklmno";\nz = [...x];\nconsole.log(z);\n// → [ \'a\', \'b\', \'c\', \'d\', \'e\', \'e\', \'f\', \'g\',\n//     \'h\', \'i\', \'j\', \'k\', \'l\', \'m\', \'n\', \'o\' ]\n\nAnd the emoji case the question is about:\n\n\'\uD83D\uDE00\'.split(\'\')   // → [ \'\uD83D\', \'\uDE00\' ]  ← two lone surrogates (broken)\n[...\'\uD83D\uDE00\']        // → [ \'\uD83D\uDE00\' ]        ← one whole character'
    },
    {
      id: 'js-06', cat: 'jsfundamentals', sub: 'strings',
      q: 'Check whether string <code>s</code> contains string <code>t</code>, ignoring case.',
      ph: 'e.g. s.toLowerCase().includes(t.toLowerCase())',
      accept: ['s.toLowerCase().includes(t.toLowerCase())', 's.toLowerCase().indexOf(t.toLowerCase()) !== -1', 's.toLowerCase().includes(t.toLowerCase());'],
      answer: 's.toLowerCase().includes(t.toLowerCase())',
      hint: 'includes() returns a boolean; indexOf() returns -1 when absent.'
    },
    {
      id: 'js-07', cat: 'jsfundamentals', sub: 'strings',
      q: 'What does <code>\'aaa\'.replace(\'a\', \'b\')</code> return — and which method replaces <em>every</em> occurrence?',
      ph: "e.g. 'aaa'.replaceAll('a', 'b')",
      accept: ["'aaa'.replaceAll('a', 'b')", '"aaa".replaceAll("a", "b")', 'replaceAll()', 's.replaceAll(a, b)'],
      answer: "'aaa'.replaceAll('a', 'b')",
      hint: 'replace() without a /g regex stops after the first match, so it returns "baa".'
    },
    {
      id: 'js-08', cat: 'jsfundamentals', sub: 'strings',
      q: 'Pad the string <code>s</code> on the left with zeros until it is 5 characters wide — the classic "format an id" trick.',
      ph: "e.g. s.padStart(5, '0')",
      accept: ["s.padStart(5, '0')", "str.padStart(5, '0')", "s.padStart(5,'0')"],
      answer: "s.padStart(5, '0')",
      hint: 'padStart(targetLength, padString) — and padEnd() for the right side.'
    },
    {
      id: 'js-09', cat: 'jsfundamentals', sub: 'strings',
      q: 'Count how many times character <code>c</code> appears in <code>s</code> in one pass, using a regex with a global flag.',
      ph: 'e.g. (s.match(/c/g) || []).length',
      accept: ['(s.match(/c/g) || []).length', '(s.match(/c/g)||[]).length', 's.split(c).length - 1'],
      answer: '(s.match(/c/g) || []).length',
      hint: 'match(/g/) returns null when there is no match — hence the || [].'
    },

    /* ── JavaScript for coding interviews: Set / Map / Object ──────────── */
    {
      id: 'js-23', cat: 'jsfundamentals', sub: 'strings',
      q: 'Interview basic: how do you get the <strong>first</strong> character of a string <code>s</code>?',
      ph: 'e.g. s.charAt(0)',
      accept: ['s.charAt(0)', 'str.charAt(0)', 'charAt(0)', 's[0]', 'str[0]', 's.at(0)'],
      answer: 's.charAt(0)',
      hint: 'All three are common: s[0], s.charAt(0), s.at(0). They differ at the edges — charAt(0) on an empty string returns \'\' while bracket access and at() return undefined.'
    },
    {
      id: 'js-10', cat: 'jsfundamentals', sub: 'types',
      q: 'Remove duplicates from an array and return a new array, preserving first-seen order. One expression.',
      ph: 'e.g. [...new Set(arr)]',
      accept: ['[...new Set(arr)]', 'Array.from(new Set(arr))', '[ ...new Set(arr) ]'],
      answer: '[...new Set(arr)]',
      hint: 'A Set holds unique values; spreading it back gives an array.'
    },
    {
      id: 'js-11', cat: 'jsfundamentals', sub: 'types',
      q: 'You need <strong>O(1) membership tests</strong> over a large list, called thousands of times. Which structure, and which method?',
      ph: 'e.g. new Set(arr) / set.has(x)',
      accept: ['set.has(x)', 'new Set(arr)', 'new Set(list)', 'set.has(val)'],
      answer: 'set.has(x)',
      hint: 'Array.includes() is O(n) per call, so a loop of them becomes O(n²).'
    },
    {
      id: 'js-12', cat: 'jsfundamentals', sub: 'types',
      q: 'How many entries does a <code>Map</code> hold — and what is the property name for it (a Map has no <code>length</code>)?',
      ph: 'e.g. map.size',
      accept: ['map.size', 'm.size', 'map.size;'],
      answer: 'map.size',
      hint: 'Same as Set — size, not length.'
    },
    {
      id: 'js-13', cat: 'jsfundamentals', sub: 'types',
      q: 'What does <code>map.get(\'missing\')</code> return for a key that was never set? (No exception.)',
      ph: 'e.g. undefined',
      accept: ['undefined', 'Undefined'],
      answer: 'undefined',
      hint: 'Which is exactly why the counting idiom needs a || 0 fallback.'
    },
    {
      id: 'js-14', cat: 'jsfundamentals', sub: 'types',
      q: 'Trap: <code>Object.keys(map)</code> returns an empty array, because Map entries are not own enumerable properties. What is the correct way to get a Map\'s keys as an array?',
      ph: 'e.g. [...map.keys()]',
      accept: ['[...map.keys()]', 'Array.from(map.keys())', 'map.keys()', '[ ...map.keys() ]'],
      answer: '[...map.keys()]',
      hint: 'map.keys() returns an iterator, not an array — spread or Array.from it.'
    },
    {
      id: 'js-15', cat: 'jsfundamentals', sub: 'types',
      q: 'Why prefer a <code>Map</code> over a plain object <code>{}</code> for a lookup table in an algorithm?',
      ph: 'e.g. keys of any type + no prototype baggage',
      accept: ['keys of any type + no prototype baggage', 'any-type keys, insertion order, no prototype', 'Map keys can be any type', 'no prototype pollution and O(1) lookups'],
      answer: 'keys of any type + no prototype baggage',
      hint: 'Object keys are coerced to strings, and obj[\'constructor\'] resolves to a real property.'
    },
    {
      id: 'js-16', cat: 'jsfundamentals', sub: 'types',
      q: 'Which loop iterates over an object\'s <strong>keys</strong> (including inherited ones) — <code>for...of</code> or <code>for...in</code>? And what does <code>for...of</code> iterate?',
      ph: 'e.g. for...in iterates keys',
      accept: ['for...in iterates keys', 'for...in over keys', 'for...in iterates keys, for...of iterates values'],
      answer: 'for...in iterates keys',
      hint: 'for...in also walks inherited *enumerable* props (Object.prototype built-ins are non-enumerable, so they stay hidden until something patches the prototype). Object.keys() or for...of avoid that.'
    },

    /* ── JavaScript for coding interviews: counting idioms ─────────────── */
    {
      id: 'js-17', cat: 'jsfundamentals', sub: 'patterns',
      q: 'The single most common LeetCode building block: count the frequency of each character <code>c</code> in <code>s</code> using a plain object. Write the line inside the loop.',
      ph: 'e.g. count[c] = (count[c] || 0) + 1',
      accept: ['count[c] = (count[c] || 0) + 1', 'freq[c] = (freq[c] || 0) + 1', 'count[c]=(count[c]||0)+1'],
      answer: 'count[c] = (count[c] || 0) + 1',
      hint: 'The || 0 turns the first occurrence (undefined) into a number.'
    },
    {
      id: 'js-18', cat: 'jsfundamentals', sub: 'patterns',
      q: 'Why is the <code>|| 0</code> necessary in <code>count[c] = (count[c] || 0) + 1</code>? What happens without it?',
      ph: 'e.g. undefined + 1 is NaN',
      accept: ['undefined + 1 is NaN', 'undefined + 1 = NaN', 'it is NaN otherwise', 'NaN', 'missing keys are undefined'],
      answer: 'undefined + 1 is NaN',
      hint: 'Once one count goes NaN the whole bucket is poisoned.'
    },
    {
      id: 'js-19', cat: 'jsfundamentals', sub: 'patterns',
      q: 'Write the same frequency count using a <code>Map</code> instead of an object.',
      ph: 'e.g. count.set(c, (count.get(c) ?? 0) + 1)',
      accept: ['count.set(c, (count.get(c) ?? 0) + 1)', 'freq.set(c, (freq.get(c) ?? 0) + 1)', 'count.set(c, (count.get(c) || 0) + 1)'],
      answer: 'count.set(c, (count.get(c) ?? 0) + 1)',
      hint: 'get() returns undefined for a missing key; ?? is the nullish-coalescing fallback.'
    },
    {
      id: 'js-20', cat: 'jsfundamentals', sub: 'patterns',
      q: 'Name the pitfall of <code>count[\'constructor\']</code> on a plain <code>{}</code>, and the object-based fix that removes it.',
      ph: 'e.g. Object.create(null)',
      accept: ['Object.create(null)', 'Object.create(null) has no prototype', 'use a Map instead', 'Object.create(null) avoids prototype lookup'],
      answer: 'Object.create(null)',
      hint: 'A plain object inherits constructor/toString, so those keys read as functions instead of undefined.'
    },
    {
      id: 'js-21', cat: 'jsfundamentals', sub: 'patterns',
      q: 'Find the largest number in an array in one expression.',
      ph: 'e.g. Math.max(...arr)',
      accept: ['Math.max(...arr)', 'Math.max.apply(null, arr)', 'Math.max(...nums)'],
      answer: 'Math.max(...arr)',
      hint: 'Beautiful, but spreading a very large array can blow the call stack — use a loop there.'
    },
    {
      id: 'js-22', cat: 'jsfundamentals', sub: 'patterns',
      q: 'Create a length-26 array of zeros — the standard letter-frequency bucket.',
      ph: 'e.g. new Array(26).fill(0)',
      accept: ['new Array(26).fill(0)', 'Array(26).fill(0)', 'new Array(26).fill(0);'],
      answer: 'new Array(26).fill(0)',
      hint: 'new Array(n) alone is sparse, so map/reduce would skip holes — fill() makes it dense.'
    }
  ]
};
