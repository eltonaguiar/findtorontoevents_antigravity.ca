// Job Resources Database - Job Boards & IT Recruiting Firms

// Comprehensive database of Canadian job boards and IT recruiting firms
const jobResources = [
  // ========== JOB BOARDS - GENERAL ==========
  {
    id: 1,
    name: 'Indeed Canada',
    url: 'https://ca.indeed.com',
    category: 'job-board-general',
    description: 'Canada\'s #1 job site with millions of listings. AI-powered matching, company reviews, and salary insights.',
    specialties: ['All Industries', 'All Levels', 'Salary Data'],
    verified: true,
    featured: true,
    icon: '🔍'
  },
  {
    id: 2,
    name: 'Job Bank (Government of Canada)',
    url: 'https://www.jobbank.gc.ca',
    category: 'job-board-gov',
    description: 'Official government job board with 50,000+ verified postings. Essential for newcomers to Canada.',
    specialties: ['Government', 'All Industries', 'Verified Listings'],
    verified: true,
    featured: true,
    icon: '🍁'
  },
  {
    id: 3,
    name: 'Eluta',
    url: 'https://www.eluta.ca',
    category: 'job-board-general',
    description: 'Specializes in unadvertised positions by scraping employer websites directly. Unique job listings.',
    specialties: ['Unadvertised Jobs', 'Direct from Companies'],
    verified: true,
    featured: true,
    icon: '🎯'
  },
  {
    id: 4,
    name: 'WowJobs',
    url: 'https://ca.wowjobs.ca',
    category: 'job-board-general',
    description: 'Job aggregator with extensive Canadian listings across all industries and experience levels.',
    specialties: ['Aggregator', 'All Industries'],
    verified: true,
    icon: '⭐'
  },
  {
    id: 5,
    name: 'SimplyHired Canada',
    url: 'https://www.simplyhired.ca',
    category: 'job-board-general',
    description: 'Aggregates 30,000+ jobs from company sites and job boards. Clean interface and salary estimates.',
    specialties: ['Aggregator', 'Salary Estimates'],
    verified: true,
    icon: '📋'
  },
  {
    id: 6,
    name: 'Workopolis',
    url: 'https://www.workopolis.com',
    category: 'job-board-general',
    description: 'Long-standing Canadian job board connecting local talent with employers. Salary info and company profiles.',
    specialties: ['Canadian Focus', 'Salary Data'],
    verified: true,
    icon: '💼'
  },
  {
    id: 7,
    name: 'Jobboom',
    url: 'https://www.jobboom.com',
    category: 'job-board-general',
    description: 'Leading Quebec job board serving English and French speakers. 16 employment sectors covered.',
    specialties: ['Quebec', 'Bilingual', 'All Sectors'],
    verified: true,
    icon: '🇫🇷'
  },
  {
    id: 8,
    name: 'CareerBuilder Canada',
    url: 'https://www.careerbuilder.ca',
    category: 'job-board-general',
    description: 'Major job board with resume builder tools and career resources for Canadian job seekers.',
    specialties: ['Resume Tools', 'Career Resources'],
    verified: true,
    icon: '🏗️'
  },
  {
    id: 9,
    name: 'CareerBeacon',
    url: 'https://www.careerbeacon.com',
    category: 'job-board-general',
    description: 'Canadian job board with salary information and provincial minimum wage data for 2026.',
    specialties: ['Salary Data', 'Canadian Focus'],
    verified: true,
    icon: '💡'
  },
  {
    id: 10,
    name: 'Jobmire',
    url: 'https://www.jobmire.com',
    category: 'job-board-general',
    description: 'One of Canada\'s top job websites with 100,000+ listings. Hundreds of new candidates daily.',
    specialties: ['High Volume', 'All Industries'],
    verified: true,
    icon: '🌐'
  },
  {
    id: 11,
    name: 'Talent.com',
    url: 'https://ca.talent.com',
    category: 'job-board-general',
    description: 'Job search platform with salary research tools and comprehensive company information.',
    specialties: ['Salary Research', 'Company Info'],
    verified: true,
    icon: '💰'
  },
  {
    id: 12,
    name: 'Jobs.ca',
    url: 'https://www.jobs.ca',
    category: 'job-board-general',
    description: 'Connects job seekers with opportunities across various industries throughout Canada.',
    specialties: ['All Industries', 'National Coverage'],
    verified: true,
    icon: '🇨🇦'
  },
  {
    id: 13,
    name: 'Monster Canada',
    url: 'https://www.monster.ca',
    category: 'job-board-general',
    description: 'Global job board with extensive career development resources and Canadian job listings.',
    specialties: ['Career Development', 'International'],
    verified: true,
    icon: '👹'
  },
  {
    id: 14,
    name: 'Glassdoor Canada',
    url: 'https://www.glassdoor.ca',
    category: 'job-board-general',
    description: 'Company reviews, salary transparency, and interview insights. Make informed career decisions.',
    specialties: ['Company Reviews', 'Salary Transparency', 'Interview Prep'],
    verified: true,
    featured: true,
    icon: '🔎'
  },
  {
    id: 15,
    name: 'ZipRecruiter Canada',
    url: 'https://www.ziprecruiter.ca',
    category: 'job-board-general',
    description: 'AI-powered job matching from businesses of all sizes across Canada.',
    specialties: ['AI Matching', 'All Business Sizes'],
    verified: true,
    icon: '⚡'
  },

  // ========== JOB BOARDS - TECH-SPECIFIC ==========
  {
    id: 16,
    name: 'LinkedIn',
    url: 'https://www.linkedin.com/jobs',
    category: 'job-board-tech',
    description: 'Essential professional network and job platform. Networking, company research, and career advancement.',
    specialties: ['Networking', 'Professional', 'All Industries'],
    verified: true,
    featured: true,
    icon: '💼'
  },
  {
    id: 17,
    name: 'We Work Remotely',
    url: 'https://weworkremotely.com',
    category: 'job-board-tech',
    description: 'Largest remote work community with tech and creative remote jobs. RSS feed available.',
    specialties: ['Remote', 'Tech', 'Creative'],
    verified: true,
    icon: '🌍'
  },
  {
    id: 18,
    name: 'RemoteOK',
    url: 'https://remoteok.com',
    category: 'job-board-tech',
    description: 'Remote tech jobs with JSON API. Popular for developers, designers, and digital nomads.',
    specialties: ['Remote', 'Tech', 'API Available'],
    verified: true,
    icon: '🖥️'
  },
  {
    id: 19,
    name: 'Remotive',
    url: 'https://remotive.com',
    category: 'job-board-tech',
    description: 'Curated remote jobs in tech, marketing, and customer support. JSON API available.',
    specialties: ['Remote', 'Tech', 'Curated'],
    verified: true,
    icon: '🏠'
  },
  {
    id: 20,
    name: 'Jobicy',
    url: 'https://jobicy.com',
    category: 'job-board-tech',
    description: 'Remote tech jobs with JSON API. Focus on software development and IT roles.',
    specialties: ['Remote', 'Software Dev', 'IT'],
    verified: true,
    icon: '💻'
  },
  {
    id: 21,
    name: 'FlexJobs',
    url: 'https://www.flexjobs.com',
    category: 'job-board-tech',
    description: 'Subscription service with vetted remote, hybrid, and flexible jobs. Quality over quantity.',
    specialties: ['Remote', 'Hybrid', 'Vetted', 'Flexible'],
    verified: true,
    icon: '✨'
  },
  {
    id: 22,
    name: 'Google for Jobs',
    url: 'https://www.google.com/search?q=jobs+near+me',
    category: 'job-board-tech',
    description: 'Aggregates jobs from across the web with advanced filters. Centralized search experience.',
    specialties: ['Aggregator', 'Search Engine', 'All Industries'],
    verified: true,
    icon: '🔍'
  },
  {
    id: 23,
    name: 'AngelList (Wellfound)',
    url: 'https://wellfound.com',
    category: 'job-board-tech',
    description: 'Startup jobs with equity information. Connect with innovative tech companies.',
    specialties: ['Startups', 'Equity', 'Tech'],
    verified: true,
    icon: '🚀'
  },
  {
    id: 24,
    name: 'Stack Overflow Jobs',
    url: 'https://stackoverflow.com/jobs',
    category: 'job-board-tech',
    description: 'Developer-focused job board from the Stack Overflow community.',
    specialties: ['Developers', 'Tech Community'],
    verified: true,
    icon: '📚'
  },
  {
    id: 25,
    name: 'EURemote',
    url: 'https://euremotejobs.com',
    category: 'job-board-tech',
    description: 'European remote jobs with RSS feed. Good for Canadian companies hiring internationally.',
    specialties: ['Remote', 'European', 'International'],
    verified: true,
    icon: '🇪🇺'
  },

  // ========== JOB BOARDS - GOVERNMENT & SPECIALIZED ==========
  {
    id: 26,
    name: 'WorkBC',
    url: 'https://www.workbc.ca',
    category: 'job-board-gov',
    description: 'British Columbia provincial job board verified with National Job Bank. BC-specific resources.',
    specialties: ['BC', 'Provincial', 'Verified'],
    verified: true,
    icon: '🏔️'
  },
  {
    id: 27,
    name: 'ECO Canada Job Board',
    url: 'https://www.eco.ca/jobs',
    category: 'job-board-gov',
    description: 'Specialized platform for environmental job opportunities across Canada.',
    specialties: ['Environmental', 'Green Jobs', 'Specialized'],
    verified: true,
    icon: '🌱'
  },

  // ========== IT RECRUITING FIRMS - NATIONAL (TIER 1) ==========
  {
    id: 28,
    name: 'Robert Half Technology',
    url: 'https://www.roberthalf.com/ca/en',
    category: 'recruiting-national',
    description: 'Global leader in IT staffing. 48-hour hiring possible. 2026 Salary Guide available. Hybrid tech/business roles.',
    specialties: ['IT', 'Finance', 'Legal', 'Healthcare', 'Permanent', 'Contract'],
    verified: true,
    featured: true,
    icon: '🏆'
  },
  {
    id: 29,
    name: 'Hays Canada',
    url: 'https://www.hays.ca',
    category: 'recruiting-national',
    description: 'Expert tech recruitment in 30+ countries. Data science, software dev, cybersecurity, cloud, DevOps. 2026 Salary Guide.',
    specialties: ['Tech', 'Data Science', 'Cybersecurity', 'Cloud', 'DevOps'],
    verified: true,
    featured: true,
    icon: '🌟'
  },
  {
    id: 30,
    name: 'Randstad Canada',
    url: 'https://www.randstad.ca',
    category: 'recruiting-national',
    description: 'Toronto HQ. Randstad Digital for digital transformation. Agile teams, outsourcing. 2026 Salary Guide.',
    specialties: ['Digital Transformation', 'Agile', 'IT', 'Enterprise'],
    verified: true,
    featured: true,
    icon: '🎯'
  },
  {
    id: 31,
    name: 'Manpower Canada',
    url: 'https://www.manpower.ca',
    category: 'recruiting-national',
    description: 'Major recruitment partner with national presence. IT and general staffing solutions.',
    specialties: ['IT', 'General Staffing', 'National'],
    verified: true,
    icon: '💪'
  },
  {
    id: 32,
    name: 'Adecco Canada',
    url: 'https://www.adecco.ca',
    category: 'recruiting-national',
    description: 'Global staffing leader with strong Canadian IT recruitment practice.',
    specialties: ['IT', 'General Staffing', 'Global'],
    verified: true,
    icon: '🌐'
  },

  // ========== IT RECRUITING FIRMS - NATIONAL (TIER 2) ==========
  {
    id: 33,
    name: 'S.i. Systems',
    url: 'https://www.sisystems.com',
    category: 'recruiting-national',
    description: 'Top-rated Canadian IT staffing agency. 300,000+ IT professionals. Contract, direct hire, payrolling. Toronto & national.',
    specialties: ['IT', 'Contract', 'Direct Hire', 'Payrolling'],
    verified: true,
    featured: true,
    icon: '🔧'
  },
  {
    id: 34,
    name: 'Modis / Akkodis Canada',
    url: 'https://www.akkodis.com/en-ca',
    category: 'recruiting-national',
    description: 'Modis merged with AKKA. 35+ years in IT/Engineering staffing. Startups to global enterprises.',
    specialties: ['IT', 'Engineering', 'Staffing Solutions'],
    verified: true,
    icon: '⚙️'
  },
  {
    id: 35,
    name: 'TEKsystems Canada',
    url: 'https://www.teksystems.com/en-ca',
    category: 'recruiting-national',
    description: 'Mississauga-based. Cloud, data, digital, DevOps, security specializations. Personalized placement support.',
    specialties: ['Cloud', 'Data', 'Digital', 'DevOps', 'Security'],
    verified: true,
    icon: '☁️'
  },
  {
    id: 36,
    name: 'Insight Global',
    url: 'https://insightglobal.com/locations/canada',
    category: 'recruiting-national',
    description: 'Global staffing agency with Canadian operations. IT, healthcare, and finance solutions.',
    specialties: ['IT', 'Healthcare', 'Finance', 'Global'],
    verified: true,
    icon: '🔍'
  },
  {
    id: 37,
    name: 'Altis Technology',
    url: 'https://www.altistechnology.com',
    category: 'recruiting-national',
    description: 'Independent Canadian IT recruitment firm. Specialized technology talent placement.',
    specialties: ['IT', 'Technology', 'Independent'],
    verified: true,
    icon: '🎓'
  },
  {
    id: 38,
    name: 'ITPlacements',
    url: 'https://www.itplacements.com',
    category: 'recruiting-national',
    description: 'Canadian IT recruitment specialist with focus on technology roles.',
    specialties: ['IT', 'Technology', 'Specialized'],
    verified: true,
    icon: '💼'
  },
  {
    id: 39,
    name: 'Direct IT Recruiting Inc.',
    url: 'https://www.directitrecruiting.com',
    category: 'recruiting-national',
    description: 'Direct IT recruitment services across Canada.',
    specialties: ['IT', 'Direct Hire', 'Canadian'],
    verified: true,
    icon: '🎯'
  },
  {
    id: 40,
    name: 'emergiTEL',
    url: 'https://www.emergitel.com',
    category: 'recruiting-national',
    description: 'IT and telecommunications recruitment specialist.',
    specialties: ['IT', 'Telecom', 'Specialized'],
    verified: true,
    icon: '📡'
  },
  {
    id: 41,
    name: 'Aerotek Canada',
    url: 'https://www.aerotek.com/en-ca',
    category: 'recruiting-national',
    description: 'Offices in AB, BC, ON, QC. Focus on industrial, skilled trades, and general staffing.',
    specialties: ['Industrial', 'Skilled Trades', 'General Staffing'],
    verified: true,
    icon: '🏭'
  },

  // ========== IT RECRUITING FIRMS - TORONTO/GTA FOCUSED ==========
  {
    id: 42,
    name: 'Lock Search Group',
    url: 'https://www.locksearchgroup.com',
    category: 'recruiting-toronto',
    description: 'Toronto-based executive search and recruitment firm.',
    specialties: ['Executive Search', 'Toronto', 'GTA'],
    verified: true,
    icon: '🔐'
  },
  {
    id: 43,
    name: 'Summit Search Group',
    url: 'https://www.summitsearchgroup.com',
    category: 'recruiting-toronto',
    description: 'Toronto recruitment firm specializing in professional placements.',
    specialties: ['Professional', 'Toronto', 'Executive'],
    verified: true,
    icon: '⛰️'
  },
  {
    id: 44,
    name: 'Michael Page Canada',
    url: 'https://www.michaelpage.ca',
    category: 'recruiting-toronto',
    description: 'Global recruitment firm with strong Toronto presence. Mid-to-senior level roles.',
    specialties: ['Mid-Senior Level', 'Toronto', 'Global'],
    verified: true,
    icon: '📄'
  },
  {
    id: 45,
    name: 'TalentGrowth Search',
    url: 'https://www.talentgrowth.ca',
    category: 'recruiting-toronto',
    description: 'Toronto-based talent acquisition and executive search.',
    specialties: ['Executive Search', 'Talent Acquisition', 'Toronto'],
    verified: true,
    icon: '🌱'
  },
  {
    id: 46,
    name: 'David Aplin Group',
    url: 'https://www.aplin.com',
    category: 'recruiting-toronto',
    description: 'Canadian recruitment firm with Toronto operations.',
    specialties: ['Professional', 'Toronto', 'Canadian'],
    verified: true,
    icon: '👔'
  },
  {
    id: 47,
    name: 'Hunt Personnel',
    url: 'https://www.huntpersonnel.com',
    category: 'recruiting-toronto',
    description: 'Toronto staffing and recruitment agency.',
    specialties: ['Staffing', 'Toronto', 'Professional'],
    verified: true,
    icon: '🎯'
  },
  {
    id: 48,
    name: 'Motion Recruitment',
    url: 'https://www.motionrecruitment.com',
    category: 'recruiting-toronto',
    description: 'Tech recruitment with Toronto presence. Active 2026 hiring.',
    specialties: ['Tech', 'Toronto', 'Active Hiring'],
    verified: true,
    icon: '🚀'
  },
  {
    id: 49,
    name: 'IQ PARTNERS',
    url: 'https://www.iqpartners.com',
    category: 'recruiting-toronto',
    description: 'Toronto-based IT and professional recruitment.',
    specialties: ['IT', 'Professional', 'Toronto'],
    verified: true,
    icon: '🧠'
  },
  {
    id: 50,
    name: 'GuruLink',
    url: 'https://www.gurulink.com',
    category: 'recruiting-toronto',
    description: 'Toronto IT recruitment and consulting services.',
    specialties: ['IT', 'Consulting', 'Toronto'],
    verified: true,
    icon: '🔗'
  },
  {
    id: 51,
    name: 'Kovasys IT Recruitment',
    url: 'https://www.kovasys.com',
    category: 'recruiting-toronto',
    description: 'Toronto-based IT recruitment specialist.',
    specialties: ['IT', 'Toronto', 'Specialized'],
    verified: true,
    icon: '💻'
  },
  {
    id: 52,
    name: 'Procom',
    url: 'https://www.procomservices.com',
    category: 'recruiting-toronto',
    description: 'Toronto IT staffing and workforce solutions.',
    specialties: ['IT Staffing', 'Workforce Solutions', 'Toronto'],
    verified: true,
    icon: '⚡'
  },
  {
    id: 53,
    name: 'Experis Canada',
    url: 'https://www.experis.ca',
    category: 'recruiting-toronto',
    description: 'IT recruitment division of ManpowerGroup with Toronto operations.',
    specialties: ['IT', 'Toronto', 'ManpowerGroup'],
    verified: true,
    icon: '🎓'
  },
  {
    id: 54,
    name: 'CORE Resources',
    url: 'https://www.coreresources.ca',
    category: 'recruiting-toronto',
    description: 'Toronto-based recruitment and staffing solutions.',
    specialties: ['Staffing', 'Toronto', 'Professional'],
    verified: true,
    icon: '🏢'
  },
  {
    id: 55,
    name: 'Robert Walters Canada',
    url: 'https://www.robertwalters.ca',
    category: 'recruiting-toronto',
    description: 'Global recruitment with Toronto presence. Professional and IT roles.',
    specialties: ['Professional', 'IT', 'Toronto', 'Global'],
    verified: true,
    icon: '🌍'
  },

  // ========== IT RECRUITING FIRMS - SPECIALIZED ==========
  {
    id: 56,
    name: 'International Financial Group (IFG)',
    url: 'https://www.ifgpr.com',
    category: 'recruiting-specialized',
    description: 'Toronto-based. Specialized in accounting, finance, and technology recruitment. Project-based and full-time.',
    specialties: ['Finance', 'Accounting', 'Technology', 'Toronto'],
    verified: true,
    icon: '💰'
  },
  {
    id: 57,
    name: 'STACK IT Recruitment',
    url: 'https://www.stackitrecruitment.com',
    category: 'recruiting-specialized',
    description: 'Specialized IT recruitment and placement agency.',
    specialties: ['IT', 'Specialized', 'Tech Focus'],
    verified: true,
    icon: '📚'
  },
  {
    id: 58,
    name: 'DevEngine',
    url: 'https://www.devengine.com',
    category: 'recruiting-specialized',
    description: 'Developer-focused recruitment and talent solutions.',
    specialties: ['Developers', 'Software Engineering', 'Tech'],
    verified: true,
    icon: '🔧'
  },
  {
    id: 59,
    name: 'OnHires',
    url: 'https://www.onhires.com',
    category: 'recruiting-specialized',
    description: 'Top IT services recruitment agency in Canada (Feb 2026).',
    specialties: ['IT Services', 'Top-Rated', 'Canadian'],
    verified: true,
    icon: '✅'
  },
  {
    id: 60,
    name: 'Solara Talent',
    url: 'https://www.solaratalent.com',
    category: 'recruiting-specialized',
    description: 'Top-ranking IT recruitment agency in Canada (Feb 2026).',
    specialties: ['IT', 'Top-Rated', 'Talent Solutions'],
    verified: true,
    icon: '☀️'
  },
  {
    id: 61,
    name: 'Wexpand',
    url: 'https://www.wexpand.com',
    category: 'recruiting-specialized',
    description: 'Top IT services recruitment agency in Canada (Feb 2026).',
    specialties: ['IT Services', 'Top-Rated', 'Expansion'],
    verified: true,
    icon: '📈'
  },
  {
    id: 62,
    name: 'StackedSP Inc.',
    url: 'https://www.stackedsp.com',
    category: 'recruiting-specialized',
    description: 'Specialized IT recruitment and staffing solutions.',
    specialties: ['IT', 'Staffing', 'Specialized'],
    verified: true,
    icon: '📊'
  },
  {
    id: 63,
    name: 'Talencore',
    url: 'https://www.talencore.com',
    category: 'recruiting-specialized',
    description: 'Core talent recruitment and placement services.',
    specialties: ['Talent Acquisition', 'IT', 'Professional'],
    verified: true,
    icon: '🎯'
  },
  {
    id: 64,
    name: 'DevTalent',
    url: 'https://www.devtalent.com',
    category: 'recruiting-specialized',
    description: 'Developer talent recruitment specialist.',
    specialties: ['Developers', 'Software', 'Tech Talent'],
    verified: true,
    icon: '👨‍💻'
  },
  {
    id: 65,
    name: 'Linkus Group',
    url: 'https://www.linkusgroup.com',
    category: 'recruiting-specialized',
    description: 'Recruitment redefined. Top IT services agency in Canada (Feb 2026).',
    specialties: ['IT Services', 'Top-Rated', 'Innovative'],
    verified: true,
    icon: '🔗'
  },
  {
    id: 66,
    name: 'DevsData Tech Talent LLC',
    url: 'https://www.devsdata.com',
    category: 'recruiting-specialized',
    description: 'Tech talent recruitment with Canadian operations.',
    specialties: ['Tech Talent', 'Developers', 'IT'],
    verified: true,
    icon: '💡'
  },
  {
    id: 67,
    name: 'ABC Recruiting Inc.',
    url: 'https://www.abcrecruiting.ca',
    category: 'recruiting-specialized',
    description: 'Top IT services recruitment in Canada (Feb 2026).',
    specialties: ['IT Services', 'Top-Rated', 'Canadian'],
    verified: true,
    icon: '🔤'
  },
  {
    id: 68,
    name: 'Philodesign Technologies',
    url: 'https://www.philodesigntech.com',
    category: 'recruiting-specialized',
    description: 'Technology-focused recruitment and IT solutions.',
    specialties: ['Technology', 'IT Solutions', 'Specialized'],
    verified: true,
    icon: '🎨'
  },
  {
    id: 69,
    name: 'HRbrain Inc.',
    url: 'https://www.hrbrain.ca',
    category: 'recruiting-specialized',
    description: 'HR and IT recruitment solutions.',
    specialties: ['HR', 'IT', 'Recruitment Solutions'],
    verified: true,
    icon: '🧠'
  },
  {
    id: 70,
    name: 'Myticas Consulting ULC',
    url: 'https://www.myticas.com',
    category: 'recruiting-specialized',
    description: 'IT consulting and recruitment services.',
    specialties: ['IT Consulting', 'Recruitment', 'Professional'],
    verified: true,
    icon: '📋'
  },
  {
    id: 71,
    name: 'Ignite Technical Resources',
    url: 'https://www.ignitetr.com',
    category: 'recruiting-specialized',
    description: 'Technical recruitment and resource solutions.',
    specialties: ['Technical', 'IT', 'Resources'],
    verified: true,
    icon: '🔥'
  },
  {
    id: 72,
    name: 'Staffmax Staffing & Recruiting',
    url: 'https://www.staffmax.ca',
    category: 'recruiting-specialized',
    description: 'Top IT staffing agency in Canada.',
    specialties: ['IT Staffing', 'Top-Rated', 'Canadian'],
    verified: true,
    icon: '👥'
  },
  {
    id: 73,
    name: 'Airswift',
    url: 'https://www.airswift.com',
    category: 'recruiting-specialized',
    description: 'Top IT staffing agency with Canadian operations.',
    specialties: ['IT Staffing', 'Global', 'Specialized'],
    verified: true,
    icon: '✈️'
  },
  {
    id: 74,
    name: 'Aplin',
    url: 'https://www.aplin.com',
    category: 'recruiting-specialized',
    description: 'Top IT staffing and recruitment agency in Canada.',
    specialties: ['IT Staffing', 'Top-Rated', 'Professional'],
    verified: true,
    icon: '🏆'
  },
  {
    id: 75,
    name: 'HR4U',
    url: 'https://www.hr4u.ca',
    category: 'recruiting-specialized',
    description: 'HR and IT recruitment solutions for Canadian businesses.',
    specialties: ['HR', 'IT', 'Canadian'],
    verified: true,
    icon: '🤝'
  }
];

// Category definitions
const categories = {
  'all': { name: 'All Resources', icon: '📚' },
  'job-board-general': { name: 'General Job Boards', icon: '📋' },
  'job-board-tech': { name: 'Tech Job Boards', icon: '💻' },
  'job-board-gov': { name: 'Government Boards', icon: '🏛️' },
  'recruiting-national': { name: 'National Recruiting Firms', icon: '🇨🇦' },
  'recruiting-toronto': { name: 'Toronto Recruiting Firms', icon: '🏙️' },
  'recruiting-specialized': { name: 'Specialized Recruiting', icon: '🎯' }
};

// State
let currentCategory = 'all';
let searchQuery = '';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  renderFeaturedResources();
  renderAllResources();
  setupEventListeners();
});

function setupEventListeners() {
  // Search
  const searchInput = document.getElementById('searchInput');
  const searchBtn = document.getElementById('searchBtn');

  searchBtn.addEventListener('click', handleSearch);
  searchInput.addEventListener('keyup', (e) => {
    if (e.key === 'Enter') handleSearch();
  });

  // Category filters
  const tagBtns = document.querySelectorAll('.tag-btn');
  tagBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tagBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentCategory = btn.dataset.category;
      renderAllResources();
    });
  });
}

function handleSearch() {
  searchQuery = document.getElementById('searchInput').value.toLowerCase();
  renderAllResources();
}

function filterResources(resourceList) {
  return resourceList.filter(resource => {
    const matchesCategory = currentCategory === 'all' || resource.category === currentCategory;
    const matchesSearch = !searchQuery ||
      resource.name.toLowerCase().includes(searchQuery) ||
      resource.description.toLowerCase().includes(searchQuery) ||
      resource.specialties.some(s => s.toLowerCase().includes(searchQuery));

    return matchesCategory && matchesSearch;
  });
}

function renderFeaturedResources() {
  const grid = document.getElementById('featuredGrid');
  const featured = jobResources.filter(r => r.featured);

  grid.innerHTML = featured.map(resource => createResourceCard(resource, true)).join('');
}

function renderAllResources() {
  const grid = document.getElementById('resourcesGrid');
  const filtered = filterResources(jobResources);

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1; text-align: center; padding: 3rem;">
        <div class="empty-state-icon" style="font-size: 4rem; margin-bottom: 1rem;">🔍</div>
        <h3>No resources found</h3>
        <p style="color: var(--text-muted); margin-top: 0.5rem;">Try adjusting your search or filters</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map(resource => createResourceCard(resource, false)).join('');
}

function createResourceCard(resource, isFeatured) {
  const categoryInfo = categories[resource.category] || { name: resource.category, icon: '📄' };
  
  return `
    <a href="${resource.url}" target="_blank" rel="noopener noreferrer" class="resource-card glass-card ${isFeatured ? 'featured' : ''}">
      <div class="resource-header">
        <div class="resource-icon">${resource.icon}</div>
        <div class="resource-meta">
          <h3 class="resource-title">${resource.name}</h3>
          <span class="resource-category">${categoryInfo.icon} ${categoryInfo.name}</span>
        </div>
      </div>
      
      <p class="resource-description">${resource.description}</p>
      
      <div class="resource-specialties">
        ${resource.specialties.map(specialty => 
          `<span class="specialty-tag">${specialty}</span>`
        ).join('')}
      </div>
      
      <div class="resource-footer">
        ${resource.verified ? '<span class="verified-badge">✓ Verified 2026</span>' : ''}
        <span class="external-link">Visit Site →</span>
      </div>
    </a>
  `;
}
