/* ═══════════════════════════════════════════════
   FriendTracker — script.js
   All data is stored in localStorage, keyed per user
   ═══════════════════════════════════════════════ */

var currentUser = null;
var friends = [];
var events = [];
var selectedTags = [];
var activeFilterTags = [];
var eventSelectedTags = [];
var eventSelectedFriends = [];

// ── Helpers ──────────────────────────────────────

var _escEl = document.createElement('div');
function esc(text) {
    if (text == null) return '';
    _escEl.textContent = text;
    return _escEl.innerHTML;
}

function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

function showToast(message, type) {
    var container = document.getElementById('toastContainer');
    var toast = document.createElement('div');
    toast.className = 'toast toast-' + (type || 'success');
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () {
        toast.classList.add('toast-out');
        setTimeout(function () { toast.remove(); }, 300);
    }, 2500);
}

function todayStr() {
    return new Date().toISOString().split('T')[0];
}

function daysBetween(dateStr1, dateStr2) {
    var d1 = new Date(dateStr1 + 'T00:00:00');
    var d2 = new Date(dateStr2 + 'T00:00:00');
    return Math.floor((d2 - d1) / (1000 * 60 * 60 * 24));
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    var d = new Date(dateStr + 'T00:00:00');
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return months[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear();
}

function timeAgo(dateStr) {
    if (!dateStr) return 'Never';
    var days = daysBetween(dateStr, todayStr());
    if (days < 0) return 'In the future';
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return days + ' days ago';
    if (days < 30) return Math.floor(days / 7) + 'w ago';
    if (days < 365) return Math.floor(days / 30) + 'mo ago';
    return Math.floor(days / 365) + 'y ago';
}

function daysUntilBirthday(birthdayStr) {
    if (!birthdayStr) return 999;
    var today = new Date();
    var bday = new Date(birthdayStr + 'T00:00:00');
    var nextBday = new Date(today.getFullYear(), bday.getMonth(), bday.getDate());
    if (nextBday < today) {
        nextBday.setFullYear(today.getFullYear() + 1);
    }
    return Math.ceil((nextBday - today) / (1000 * 60 * 60 * 24));
}

function getInitials(name) {
    return name.split(/\s+/).filter(Boolean).map(function (w) { return w[0].toUpperCase(); }).slice(0, 2).join('');
}

// ── Photo Upload ────────────────────────────────

var pendingPhoto = null; // base64 string for current form

function handlePhotoUpload(e) {
    var file = e.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
        showToast('Please select an image file', 'error');
        return;
    }
    // Max 5MB raw input
    if (file.size > 5 * 1024 * 1024) {
        showToast('Image too large (max 5MB)', 'error');
        return;
    }

    var reader = new FileReader();
    reader.onload = function (ev) {
        compressImage(ev.target.result, 200, 0.7, function (compressed) {
            pendingPhoto = compressed;
            var img = document.getElementById('avatarPreviewImg');
            img.src = compressed;
            img.classList.remove('hidden');
            document.getElementById('avatarPreviewInitials').classList.add('hidden');
            document.getElementById('removePhotoBtn').classList.remove('hidden');
        });
    };
    reader.readAsDataURL(file);
}

function compressImage(dataUrl, maxSize, quality, callback) {
    var img = new Image();
    img.onload = function () {
        var canvas = document.createElement('canvas');
        var w = img.width;
        var h = img.height;

        // Scale down to maxSize x maxSize box
        if (w > maxSize || h > maxSize) {
            if (w > h) {
                h = Math.round(h * maxSize / w);
                w = maxSize;
            } else {
                w = Math.round(w * maxSize / h);
                h = maxSize;
            }
        }

        canvas.width = w;
        canvas.height = h;
        var ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, w, h);
        callback(canvas.toDataURL('image/jpeg', quality));
    };
    img.src = dataUrl;
}

function removePhoto() {
    pendingPhoto = '';
    document.getElementById('friendPhoto').value = '';
    document.getElementById('avatarPreviewImg').classList.add('hidden');
    document.getElementById('avatarPreviewImg').src = '';
    document.getElementById('avatarPreviewInitials').classList.remove('hidden');
    document.getElementById('removePhotoBtn').classList.add('hidden');
}

function updateAvatarPreview() {
    var name = document.getElementById('friendName').value.trim();
    var initialsEl = document.getElementById('avatarPreviewInitials');
    initialsEl.textContent = name ? getInitials(name) : '?';
}

// ── API Service ────────────────────────────────

var API_BASE = (location.hostname === 'localhost' || location.protocol === 'file:')
    ? '../favcreators/docs/api'
    : '/fc/api';

// Helper: fetch JSON with error handling
function apiFetch(endpoint, options) {
    var url = API_BASE + '/' + endpoint;
    var opts = Object.assign({ credentials: 'include' }, options);
    return fetch(url, opts)
        .then(function (response) {
            if (!response.ok) {
                throw new Error('API error ' + response.status);
            }
            return response.json();
        })
        .catch(function (err) {
            console.warn('API fetch failed for ' + endpoint + ': ' + err.message);
            throw err;
        });
}

// ── Storage (per-user) ──────────────────────────

function storageKey(key) {
    return 'ft_' + currentUser + '_' + key;
}

function loadFriends() {
    // Try API first
    apiFetch('ft_get_friends.php')
        .then(function (data) {
            friends = data.friends || [];
            // Cache in localStorage
            localStorage.setItem(storageKey('friends'), JSON.stringify(friends));
            renderTagFilters();
            renderFriends();
            updateStats();
        })
        .catch(function () {
            // Fallback to localStorage
            var data = localStorage.getItem(storageKey('friends'));
            friends = data ? JSON.parse(data) : [];
            renderTagFilters();
            renderFriends();
            updateStats();
        });
}

function saveFriends() {
    // Cache in localStorage
    localStorage.setItem(storageKey('friends'), JSON.stringify(friends));
    // Sync to API in background (no await)
    // Note: For individual friend saves, use saveFriend API directly
}

function loadEvents() {
    // Try API first
    apiFetch('ft_get_events.php')
        .then(function (data) {
            events = data.events || [];
            localStorage.setItem(storageKey('events'), JSON.stringify(events));
            renderEvents();
        })
        .catch(function () {
            var data = localStorage.getItem(storageKey('events'));
            events = data ? JSON.parse(data) : [];
            renderEvents();
        });
}

function saveEvents() {
    localStorage.setItem(storageKey('events'), JSON.stringify(events));
    // Sync to API in background
}

function getUsers() {
    var data = localStorage.getItem('ft_users');
    return data ? JSON.parse(data) : {};
}

function saveUsers(users) {
    localStorage.setItem('ft_users', JSON.stringify(users));
}

// ── Auth ─────────────────────────────────────────

function switchAuthTab(tab) {
    document.querySelectorAll('.auth-tab').forEach(function (t) { t.classList.remove('active'); });
    document.querySelector('[data-tab="' + tab + '"]').classList.add('active');
    document.getElementById('loginForm').classList.toggle('hidden', tab !== 'login');
    document.getElementById('registerForm').classList.toggle('hidden', tab !== 'register');
    document.getElementById('authError').classList.add('hidden');
}

function showAuthError(msg) {
    var el = document.getElementById('authError');
    el.textContent = msg;
    el.classList.remove('hidden');
}

function handleLogin(e) {
    e.preventDefault();
    var email = document.getElementById('loginUsername').value.trim().toLowerCase();
    var password = document.getElementById('loginPassword').value;

    // Try API login
    apiFetch('login.php', {
        method: 'POST',
        body: JSON.stringify({ email: email, password: password }),
        headers: { 'Content-Type': 'application/json' }
    })
    .then(function (data) {
        if (data.error) {
            // If it's a server/DB error, fall back to localStorage
            if (data.error.toLowerCase().indexOf('database') >= 0 ||
                data.error.toLowerCase().indexOf('connection') >= 0) {
                throw new Error(data.error);
            }
            showAuthError(data.error);
            return;
        }
        // Success: store user info locally as fallback
        var users = getUsers();
        users[email] = { password: password, created: todayStr() };
        saveUsers(users);

        currentUser = email;
        localStorage.setItem('ft_currentUser', email);
        enterApp();
    })
    .catch(function (err) {
        console.warn('API login failed, falling back to localStorage:', err.message);
        // Fallback to localStorage authentication
        var users = getUsers();
        if (!users[email]) {
            showAuthError('User not found. Create an account first.');
            return;
        }
        if (users[email].password !== password) {
            showAuthError('Incorrect password.');
            return;
        }
        currentUser = email;
        localStorage.setItem('ft_currentUser', email);
        enterApp();
    });
}

function handleRegister(e) {
    e.preventDefault();
    var username = document.getElementById('regUsername').value.trim().toLowerCase();
    var password = document.getElementById('regPassword').value;
    var confirm = document.getElementById('regPasswordConfirm').value;

    if (username.length < 2) {
        showAuthError('Username must be at least 2 characters.');
        return;
    }
    if (password.length < 3) {
        showAuthError('Password must be at least 3 characters.');
        return;
    }
    if (password !== confirm) {
        showAuthError('Passwords do not match.');
        return;
    }

    var users = getUsers();
    if (users[username]) {
        showAuthError('Username already taken.');
        return;
    }

    users[username] = { password: password, created: todayStr() };
    saveUsers(users);

    currentUser = username;
    localStorage.setItem('ft_currentUser', username);
    enterApp();
    showToast('Account created! Welcome, ' + username + ' 🎉');
}

function handleLogout() {
    currentUser = null;
    localStorage.removeItem('ft_currentUser');
    document.getElementById('app').classList.add('hidden');
    document.getElementById('authScreen').classList.remove('hidden');
    document.getElementById('userDropdown').classList.add('hidden');
    document.getElementById('loginUsername').value = '';
    document.getElementById('loginPassword').value = '';
}

function enterApp() {
    document.getElementById('authScreen').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');

    var btn = document.getElementById('userBtn');
    btn.textContent = getInitials(currentUser);
    document.getElementById('userDropdownName').textContent = currentUser;

    loadFriends();
    loadEvents();
    renderTagFilters();
    renderFriends();
    renderEvents();
    updateStats();
}

function toggleUserMenu() {
    document.getElementById('userDropdown').classList.toggle('hidden');
}

// Close dropdown on outside click
document.addEventListener('click', function (e) {
    if (!e.target.closest('.user-menu')) {
        document.getElementById('userDropdown').classList.add('hidden');
    }
});

// Close modals on Escape key
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        var modals = ['eventDetailModal', 'eventModal', 'hangoutModal', 'detailModal', 'friendModal', 'importModal'];
        for (var i = 0; i < modals.length; i++) {
            var el = document.getElementById(modals[i]);
            if (el && !el.classList.contains('hidden')) {
                el.classList.add('hidden');
                return;
            }
        }
    }
});

// Close modal on overlay click
function handleOverlayClick(e, modalId) {
    if (e.target === e.currentTarget) {
        document.getElementById(modalId).classList.add('hidden');
    }
}

// ── Tag Management ──────────────────────────────

function getAllTags() {
    var tags = {};
    friends.forEach(function (f) {
        (f.tags || []).forEach(function (t) {
            tags[t] = (tags[t] || 0) + 1;
        });
    });
    return tags;
}

function renderTagFilters() {
    var tags = getAllTags();
    var container = document.getElementById('tagFilters');
    var sorted = Object.keys(tags).sort(function (a, b) { return tags[b] - tags[a]; });

    container.innerHTML = sorted.map(function (tag) {
        var isActive = activeFilterTags.indexOf(tag) >= 0;
        return '<button class="tag-filter' + (isActive ? ' active' : '') + '" onclick="toggleFilterTag(\'' + esc(tag.replace(/'/g, "\\'")) + '\')">' +
            esc(tag) + ' (' + tags[tag] + ')</button>';
    }).join('');
}

function toggleFilterTag(tag) {
    var idx = activeFilterTags.indexOf(tag);
    if (idx >= 0) {
        activeFilterTags.splice(idx, 1);
    } else {
        activeFilterTags.push(tag);
    }
    renderTagFilters();
    renderFriends();
}

function renderSelectedTags() {
    var container = document.getElementById('selectedTags');
    container.innerHTML = selectedTags.map(function (tag) {
        return '<span class="selected-tag">' + esc(tag) +
            '<span class="remove-tag" onclick="removeTag(\'' + esc(tag.replace(/'/g, "\\'")) + '\')">✕</span></span>';
    }).join('');
}

function addTag(tag) {
    tag = tag.trim();
    if (!tag) return;
    if (selectedTags.indexOf(tag) >= 0) return;
    selectedTags.push(tag);
    renderSelectedTags();
    document.getElementById('tagInput').value = '';
    document.getElementById('tagSuggestions').innerHTML = '';
}

function removeTag(tag) {
    selectedTags = selectedTags.filter(function (t) { return t !== tag; });
    renderSelectedTags();
}

function handleTagKeydown(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        var val = document.getElementById('tagInput').value.trim();
        if (val) addTag(val);
    }
    if (e.key === 'Backspace' && !document.getElementById('tagInput').value && selectedTags.length > 0) {
        selectedTags.pop();
        renderSelectedTags();
    }
}

function filterTagSuggestions() {
    var val = document.getElementById('tagInput').value.trim().toLowerCase();
    var container = document.getElementById('tagSuggestions');
    if (!val) {
        container.innerHTML = '';
        return;
    }

    var allTags = Object.keys(getAllTags());
    var matches = allTags.filter(function (t) {
        return t.toLowerCase().includes(val) && selectedTags.indexOf(t) < 0;
    }).slice(0, 8);

    container.innerHTML = matches.map(function (tag) {
        return '<button type="button" class="tag-suggestion" onclick="addTag(\'' + esc(tag.replace(/'/g, "\\'")) + '\')">' + esc(tag) + '</button>';
    }).join('');
}

// ── Friends CRUD ────────────────────────────────

function openAddFriend() {
    document.getElementById('modalTitle').textContent = 'Add Friend';
    document.getElementById('saveBtn').textContent = 'Save Friend';
    document.getElementById('friendForm').reset();
    document.getElementById('friendId').value = '';
    selectedTags = [];
    pendingPhoto = null;
    renderSelectedTags();
    document.getElementById('tagSuggestions').innerHTML = '';
    // Reset avatar preview
    document.getElementById('avatarPreviewImg').classList.add('hidden');
    document.getElementById('avatarPreviewImg').src = '';
    document.getElementById('avatarPreviewInitials').classList.remove('hidden');
    document.getElementById('avatarPreviewInitials').textContent = '?';
    document.getElementById('removePhotoBtn').classList.add('hidden');
    document.getElementById('friendModal').classList.remove('hidden');
}

function openEditFriend(id) {
    var friend = friends.find(function (f) { return f.id === id; });
    if (!friend) return;

    document.getElementById('modalTitle').textContent = 'Edit Friend';
    document.getElementById('saveBtn').textContent = 'Update Friend';
    document.getElementById('friendId').value = friend.id;
    document.getElementById('friendName').value = friend.name || '';
    document.getElementById('friendNickname').value = friend.nickname || '';
    document.getElementById('friendBirthday').value = friend.birthday || '';
    document.getElementById('friendHowMet').value = friend.howMet || '';
    document.getElementById('friendNotes').value = friend.notes || '';
    document.getElementById('friendPhone').value = friend.phone || '';
    document.getElementById('friendEmail').value = friend.email || '';
    document.getElementById('friendInstagram').value = friend.instagram || '';
    document.getElementById('friendTiktok').value = friend.tiktok || '';
    document.getElementById('friendTwitter').value = friend.twitter || '';
    document.getElementById('friendSnapchat').value = friend.snapchat || '';
    document.getElementById('friendLinkedin').value = friend.linkedin || '';
    document.getElementById('friendOtherSocial').value = friend.otherSocial || '';
    document.getElementById('friendCadence').value = friend.cadenceDays || '';

    // Load photo
    pendingPhoto = friend.photo || null;
    if (friend.photo) {
        document.getElementById('avatarPreviewImg').src = friend.photo;
        document.getElementById('avatarPreviewImg').classList.remove('hidden');
        document.getElementById('avatarPreviewInitials').classList.add('hidden');
        document.getElementById('removePhotoBtn').classList.remove('hidden');
    } else {
        document.getElementById('avatarPreviewImg').classList.add('hidden');
        document.getElementById('avatarPreviewImg').src = '';
        document.getElementById('avatarPreviewInitials').classList.remove('hidden');
        document.getElementById('avatarPreviewInitials').textContent = getInitials(friend.name);
        document.getElementById('removePhotoBtn').classList.add('hidden');
    }

    selectedTags = (friend.tags || []).slice();
    renderSelectedTags();
    document.getElementById('tagSuggestions').innerHTML = '';
    document.getElementById('friendModal').classList.remove('hidden');
}

function closeFriendModal() {
    document.getElementById('friendModal').classList.add('hidden');
}

function saveFriend(e) {
    e.preventDefault();
    var id = document.getElementById('friendId').value;
    var isNew = !id;

    var data = {
        id: id || generateId(),
        name: document.getElementById('friendName').value.trim(),
        nickname: document.getElementById('friendNickname').value.trim(),
        birthday: document.getElementById('friendBirthday').value,
        howMet: document.getElementById('friendHowMet').value.trim(),
        notes: document.getElementById('friendNotes').value.trim(),
        phone: document.getElementById('friendPhone').value.trim(),
        email: document.getElementById('friendEmail').value.trim(),
        instagram: document.getElementById('friendInstagram').value.trim(),
        tiktok: document.getElementById('friendTiktok').value.trim(),
        twitter: document.getElementById('friendTwitter').value.trim(),
        snapchat: document.getElementById('friendSnapchat').value.trim(),
        linkedin: document.getElementById('friendLinkedin').value.trim(),
        otherSocial: document.getElementById('friendOtherSocial').value.trim(),
        tags: selectedTags.slice(),
        cadenceDays: document.getElementById('friendCadence').value ? parseInt(document.getElementById('friendCadence').value) : null,
        photo: pendingPhoto !== null ? pendingPhoto : undefined,
        hangouts: [],
        createdAt: todayStr()
    };

    // Preserve photo from existing friend if not changed
    if (pendingPhoto === null && !isNew) {
        var existing = friends.find(function (f) { return f.id === id; });
        if (existing) data.photo = existing.photo || '';
    }

    // Try API first
    apiFetch('ft_save_friend.php', {
        method: 'POST',
        body: JSON.stringify(data),
        headers: { 'Content-Type': 'application/json' }
    })
    .then(function (response) {
        if (response.error) {
            throw new Error(response.error);
        }
        // API success: update local friend with returned data
        var savedFriend = response.friend;
        var idx = friends.findIndex(function (f) { return f.id === savedFriend.id; });
        if (idx >= 0) {
            friends[idx] = savedFriend;
        } else {
            friends.push(savedFriend);
        }
        showToast((isNew ? 'Added ' : 'Updated ') + savedFriend.name + (isNew ? '! 🎉' : ' ✅'));
        saveFriends(); // cache in localStorage
        closeFriendModal();
        renderTagFilters();
        renderFriends();
        updateStats();
    })
    .catch(function (err) {
        console.warn('API save failed, using localStorage only:', err.message);
        // Fallback to localStorage only
        if (isNew) {
            friends.push(data);
            showToast('Added ' + data.name + '! 🎉');
        } else {
            var idx = friends.findIndex(function (f) { return f.id === id; });
            if (idx >= 0) {
                data.hangouts = friends[idx].hangouts || [];
                data.createdAt = friends[idx].createdAt || todayStr();
                friends[idx] = data;
            }
            showToast('Updated ' + data.name + ' ✅');
        }
        saveFriends();
        closeFriendModal();
        renderTagFilters();
        renderFriends();
        updateStats();
    });
}

function deleteFriend(id) {
    var friend = friends.find(function (f) { return f.id === id; });
    if (!friend) return;
    if (!confirm('Delete ' + friend.name + '? This cannot be undone.')) return;

    friends = friends.filter(function (f) { return f.id !== id; });
    saveFriends();
    renderTagFilters();
    renderFriends();
    updateStats();
    closeDetailModal();
    showToast('Deleted ' + friend.name);
}

// ── Hangouts ────────────────────────────────────

function openHangoutModal(id) {
    document.getElementById('hangoutFriendId').value = id;
    document.getElementById('hangoutDate').value = todayStr();
    document.getElementById('hangoutActivity').value = '';
    document.getElementById('hangoutNotes').value = '';
    document.getElementById('hangoutModal').classList.remove('hidden');
}

function closeHangoutModal() {
    document.getElementById('hangoutModal').classList.add('hidden');
}

function saveHangout(e) {
    e.preventDefault();
    var friendId = document.getElementById('hangoutFriendId').value;
    var friend = friends.find(function (f) { return f.id === friendId; });
    if (!friend) return;

    if (!friend.hangouts) friend.hangouts = [];
    friend.hangouts.push({
        id: generateId(),
        date: document.getElementById('hangoutDate').value,
        activity: document.getElementById('hangoutActivity').value.trim(),
        notes: document.getElementById('hangoutNotes').value.trim()
    });

    friend.hangouts.sort(function (a, b) { return b.date.localeCompare(a.date); });

    saveFriends();
    closeHangoutModal();
    renderFriends();
    updateStats();
    showToast('Hangout logged with ' + friend.name + '! 🤝');

    if (document.getElementById('detailModal').classList.contains('hidden') === false) {
        openDetailModal(friendId);
    }
}

function deleteHangout(friendId, hangoutId) {
    var friend = friends.find(function (f) { return f.id === friendId; });
    if (!friend) return;
    friend.hangouts = (friend.hangouts || []).filter(function (h) { return h.id !== hangoutId; });
    saveFriends();
    renderFriends();
    updateStats();
    openDetailModal(friendId);
}

function getLastSeen(friend) {
    if (!friend.hangouts || friend.hangouts.length === 0) return null;
    return friend.hangouts[0].date;
}

function getTimesSeenCount(friend) {
    return (friend.hangouts || []).length;
}

// ── Cadence ─────────────────────────────────────

function getCadenceStatus(friend) {
    if (!friend.cadenceDays) return null;
    var lastSeen = getLastSeen(friend);
    if (!lastSeen) return { percent: 100, status: 'overdue', daysOverdue: friend.cadenceDays };

    var daysSince = daysBetween(lastSeen, todayStr());
    var percent = Math.min(100, Math.round((daysSince / friend.cadenceDays) * 100));

    if (percent <= 60) return { percent: percent, status: 'good', daysOverdue: 0 };
    if (percent <= 100) return { percent: percent, status: 'warn', daysOverdue: 0 };
    return { percent: 100, status: 'overdue', daysOverdue: daysSince - friend.cadenceDays };
}

// ── Rendering ───────────────────────────────────

function getFilteredFriends() {
    var query = document.getElementById('searchInput').value.toLowerCase().trim();
    var sort = document.getElementById('sortSelect').value;

    var result = friends.filter(function (f) {
        if (query) {
            var searchable = (f.name + ' ' + (f.nickname || '') + ' ' + (f.notes || '') + ' ' + (f.tags || []).join(' ')).toLowerCase();
            if (!searchable.includes(query)) return false;
        }
        if (activeFilterTags.length > 0) {
            var hasTags = activeFilterTags.every(function (tag) {
                return (f.tags || []).indexOf(tag) >= 0;
            });
            if (!hasTags) return false;
        }
        return true;
    });

    result.sort(function (a, b) {
        switch (sort) {
            case 'name-asc':
                return a.name.localeCompare(b.name);
            case 'name-desc':
                return b.name.localeCompare(a.name);
            case 'last-seen': {
                var aDate = getLastSeen(a) || '1900-01-01';
                var bDate = getLastSeen(b) || '1900-01-01';
                return bDate.localeCompare(aDate);
            }
            case 'most-seen':
                return getTimesSeenCount(b) - getTimesSeenCount(a);
            case 'least-seen':
                return getTimesSeenCount(a) - getTimesSeenCount(b);
            case 'birthday-upcoming':
                return daysUntilBirthday(a.birthday) - daysUntilBirthday(b.birthday);
            case 'needs-attention': {
                var aCadence = getCadenceStatus(a);
                var bCadence = getCadenceStatus(b);
                var aScore = aCadence ? aCadence.percent : -1;
                var bScore = bCadence ? bCadence.percent : -1;
                return bScore - aScore;
            }
            default:
                return 0;
        }
    });

    return result;
}

function renderFriends() {
    var filtered = getFilteredFriends();
    var list = document.getElementById('friendsList');
    var empty = document.getElementById('emptyState');

    if (friends.length === 0) {
        empty.classList.remove('hidden');
        list.innerHTML = '';
        return;
    }
    empty.classList.add('hidden');

    if (filtered.length === 0) {
        list.innerHTML = '<div style="text-align:center;padding:40px;opacity:0.5;">No friends match your filters</div>';
        return;
    }

    list.innerHTML = filtered.map(function (f) {
        var lastSeen = getLastSeen(f);
        var timesCount = getTimesSeenCount(f);
        var cadence = getCadenceStatus(f);
        var bdayDays = daysUntilBirthday(f.birthday);
        var bdayBadge = '';
        if (bdayDays <= 30 && f.birthday) {
            bdayBadge = '<span class="friend-birthday-badge">🎂 ' +
                (bdayDays === 0 ? 'Today!' : bdayDays === 1 ? 'Tomorrow!' : 'In ' + bdayDays + 'd') + '</span>';
        }

        var avatarClass = 'friend-avatar';
        if (cadence && cadence.status === 'overdue') avatarClass += ' overdue';
        else if (bdayDays <= 7 && f.birthday) avatarClass += ' birthday-soon';

        var cadenceBar = '';
        if (cadence) {
            cadenceBar = '<div class="friend-cadence-bar"><div class="friend-cadence-fill cadence-' + cadence.status + '" style="width:' + cadence.percent + '%"></div></div>';
        }

        var tagsHtml = (f.tags || []).slice(0, 4).map(function (t) {
            return '<span class="friend-tag">' + esc(t) + '</span>';
        }).join('');
        if ((f.tags || []).length > 4) {
            tagsHtml += '<span class="friend-tag">+' + ((f.tags || []).length - 4) + '</span>';
        }

        return '<div class="friend-card" onclick="openDetailModal(\'' + f.id + '\')">' +
            '<div class="friend-card-actions">' +
                '<button class="card-action-btn" onclick="event.stopPropagation(); openHangoutModal(\'' + f.id + '\')" title="Log Hangout">📅</button>' +
                '<button class="card-action-btn" onclick="event.stopPropagation(); openEditFriend(\'' + f.id + '\')" title="Edit">✏️</button>' +
                '<button class="card-action-btn danger" onclick="event.stopPropagation(); deleteFriend(\'' + f.id + '\')" title="Delete">🗑</button>' +
            '</div>' +
            '<div class="friend-card-top">' +
                '<div class="' + avatarClass + '">' + (f.photo ? '<img src="' + f.photo + '" alt="' + esc(f.name) + '">' : esc(getInitials(f.name))) + '</div>' +
                '<div class="friend-info">' +
                    '<div class="friend-name">' + esc(f.name) + bdayBadge + '</div>' +
                    (f.nickname ? '<div class="friend-nickname">"' + esc(f.nickname) + '"</div>' : '') +
                '</div>' +
            '</div>' +
            '<div class="friend-meta">' +
                '<span class="friend-meta-item">👀 ' + timeAgo(lastSeen) + '</span>' +
                '<span class="friend-meta-item">🤝 ' + timesCount + 'x</span>' +
                (cadence && cadence.status === 'overdue' ? '<span class="friend-meta-item" style="color:#f87171;">⚠️ ' + cadence.daysOverdue + 'd overdue</span>' : '') +
            '</div>' +
            (tagsHtml ? '<div class="friend-tags">' + tagsHtml + '</div>' : '') +
            cadenceBar +
        '</div>';
    }).join('');
}

// ── Detail Modal ────────────────────────────────

function openDetailModal(id) {
    var friend = friends.find(function (f) { return f.id === id; });
    if (!friend) return;

    document.getElementById('detailName').textContent = friend.name + (friend.nickname ? ' ("' + friend.nickname + '")' : '');
    var content = document.getElementById('detailContent');

    var lastSeen = getLastSeen(friend);
    var timesCount = getTimesSeenCount(friend);
    var cadence = getCadenceStatus(friend);

    var html = '';

    // Photo header
    if (friend.photo) {
        html += '<div style="text-align:center;margin-bottom:16px;"><div class="friend-avatar" style="width:80px;height:80px;margin:0 auto;font-size:32px;"><img src="' + friend.photo + '" alt="' + esc(friend.name) + '"></div></div>';
    }

    // Overview
    html += '<div class="detail-section"><div class="detail-section-title">Overview</div><div class="detail-grid">';
    html += '<div class="detail-item"><div class="detail-item-label">Times Seen</div><div class="detail-item-value">' + timesCount + '</div></div>';
    html += '<div class="detail-item"><div class="detail-item-label">Last Seen</div><div class="detail-item-value">' + (lastSeen ? formatDate(lastSeen) + ' (' + timeAgo(lastSeen) + ')' : 'Never') + '</div></div>';
    if (friend.birthday) {
        var bdayDays = daysUntilBirthday(friend.birthday);
        html += '<div class="detail-item"><div class="detail-item-label">🎂 Birthday</div><div class="detail-item-value">' + formatDate(friend.birthday) + ' (' + (bdayDays === 0 ? 'Today!' : 'in ' + bdayDays + ' days') + ')</div></div>';
    }
    if (friend.howMet) {
        html += '<div class="detail-item"><div class="detail-item-label">How You Met</div><div class="detail-item-value">' + esc(friend.howMet) + '</div></div>';
    }
    if (cadence) {
        var cadenceLabel = cadence.status === 'good' ? '✅ On track' : cadence.status === 'warn' ? '⚠️ Due soon' : '🔴 ' + cadence.daysOverdue + ' days overdue';
        html += '<div class="detail-item"><div class="detail-item-label">Cadence</div><div class="detail-item-value">' + cadenceLabel + ' (every ' + friend.cadenceDays + 'd)</div></div>';
    }
    if (friend.notes) {
        html += '<div class="detail-item" style="grid-column:1/-1"><div class="detail-item-label">Notes</div><div class="detail-item-value" style="word-break:normal">' + esc(friend.notes) + '</div></div>';
    }
    html += '</div></div>';

    // Contact & Social
    var socials = [];
    if (friend.phone) socials.push({ label: '📱 Phone', value: friend.phone, href: 'tel:' + friend.phone });
    if (friend.email) socials.push({ label: '📧 Email', value: friend.email, href: 'mailto:' + friend.email });
    if (friend.instagram) socials.push({ label: '📸 Instagram', value: friend.instagram, href: 'https://instagram.com/' + friend.instagram.replace('@', '') });
    if (friend.tiktok) socials.push({ label: '🎵 TikTok', value: friend.tiktok, href: 'https://tiktok.com/@' + friend.tiktok.replace('@', '') });
    if (friend.twitter) socials.push({ label: '🐦 Twitter/X', value: friend.twitter, href: 'https://x.com/' + friend.twitter.replace('@', '') });
    if (friend.snapchat) socials.push({ label: '💬 Snapchat', value: friend.snapchat, href: null });
    if (friend.linkedin) socials.push({ label: '💼 LinkedIn', value: friend.linkedin, href: friend.linkedin.includes('http') ? friend.linkedin : 'https://linkedin.com/in/' + friend.linkedin });
    if (friend.otherSocial) socials.push({ label: '🔗 Other', value: friend.otherSocial, href: friend.otherSocial.includes('http') ? friend.otherSocial : null });

    if (socials.length > 0) {
        html += '<div class="detail-section"><div class="detail-section-title">Contact & Social Media</div><div class="detail-grid">';
        socials.forEach(function (s) {
            var valHtml = s.href
                ? '<a href="' + esc(s.href) + '" target="_blank" rel="noopener">' + esc(s.value) + '</a>'
                : esc(s.value);
            html += '<div class="detail-item"><div class="detail-item-label">' + s.label + '</div><div class="detail-item-value">' + valHtml + '</div></div>';
        });
        html += '</div></div>';
    }

    // Tags
    if (friend.tags && friend.tags.length > 0) {
        html += '<div class="detail-section"><div class="detail-section-title">Tags</div><div class="detail-tags">';
        friend.tags.forEach(function (t) {
            html += '<span class="detail-tag">' + esc(t) + '</span>';
        });
        html += '</div></div>';
    }

    // Hangout History
    html += '<div class="detail-section"><div class="detail-section-title">Hangout History (' + timesCount + ')</div>';
    if (friend.hangouts && friend.hangouts.length > 0) {
        html += '<div class="hangout-list">';
        friend.hangouts.forEach(function (h) {
            html += '<div class="hangout-item">' +
                '<span class="hangout-date">' + formatDate(h.date) + '</span>' +
                '<span class="hangout-activity">' + (h.activity ? esc(h.activity) : '<span style="opacity:0.4">No activity</span>') +
                    (h.notes ? ' <span style="opacity:0.4">— ' + esc(h.notes) + '</span>' : '') + '</span>' +
                '<button class="hangout-delete" onclick="deleteHangout(\'' + friend.id + '\', \'' + h.id + '\')" title="Delete">✕</button>' +
            '</div>';
        });
        html += '</div>';
    } else {
        html += '<div style="opacity:0.4;font-size:13px;">No hangouts logged yet</div>';
    }
    html += '</div>';

    // Actions
    html += '<div class="detail-actions">';
    html += '<button class="btn-primary" onclick="openHangoutModal(\'' + friend.id + '\')">📅 Log Hangout</button>';
    html += '<button class="btn-secondary" onclick="closeDetailModal(); openEditFriend(\'' + friend.id + '\')">✏️ Edit</button>';
    html += '<button class="btn-danger" onclick="deleteFriend(\'' + friend.id + '\')">🗑 Delete</button>';
    html += '</div>';

    content.innerHTML = html;
    document.getElementById('detailModal').classList.remove('hidden');
}

function closeDetailModal() {
    document.getElementById('detailModal').classList.add('hidden');
}

// ── Stats ───────────────────────────────────────

function toggleStats() {
    document.getElementById('statsPanel').classList.toggle('hidden');
    updateStats();
}

function updateStats() {
    var now = new Date();
    var thisMonth = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');

    var seenThisMonth = 0;
    var needsAttention = 0;
    var birthdaysThisMonth = 0;

    friends.forEach(function (f) {
        var hangoutsThisMonth = (f.hangouts || []).filter(function (h) {
            return h.date && h.date.startsWith(thisMonth);
        });
        if (hangoutsThisMonth.length > 0) seenThisMonth++;

        var cadence = getCadenceStatus(f);
        if (cadence && cadence.status === 'overdue') needsAttention++;

        if (f.birthday) {
            var bday = new Date(f.birthday + 'T00:00:00');
            if (bday.getMonth() === now.getMonth()) birthdaysThisMonth++;
        }
    });

    document.getElementById('statTotal').textContent = friends.length;
    document.getElementById('statSeenThisMonth').textContent = seenThisMonth;
    document.getElementById('statNeedsAttention').textContent = needsAttention;
    document.getElementById('statBirthdays').textContent = birthdaysThisMonth;
}

// ── Export / Import ─────────────────────────────

function exportData() {
    var data = JSON.stringify({ friends: friends, events: events }, null, 2);
    var blob = new Blob([data], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'friendtracker-' + currentUser + '-' + todayStr() + '.json';
    a.click();
    URL.revokeObjectURL(url);
    showToast('Data exported! 📥');
    document.getElementById('userDropdown').classList.add('hidden');
}

function importDataPrompt() {
    document.getElementById('importModal').classList.remove('hidden');
    document.getElementById('importData').value = '';
    document.getElementById('userDropdown').classList.add('hidden');
}

function closeImportModal() {
    document.getElementById('importModal').classList.add('hidden');
}

function importData() {
    var raw = document.getElementById('importData').value.trim();
    if (!raw) {
        showToast('Please paste your data first', 'error');
        return;
    }

    try {
        var data = JSON.parse(raw);
        var friendsArr = [];
        var eventsArr = [];

        if (Array.isArray(data)) {
            friendsArr = data;
        } else if (data && typeof data === 'object') {
            friendsArr = Array.isArray(data.friends) ? data.friends : [];
            eventsArr = Array.isArray(data.events) ? data.events : [];
        } else {
            throw new Error('Invalid format');
        }

        var imported = 0;
        friendsArr.forEach(function (item) {
            if (!item.name) return;
            if (!item.id) item.id = generateId();
            if (!friends.find(function (f) { return f.id === item.id; })) {
                friends.push(item);
                imported++;
            }
        });

        var importedEvents = 0;
        eventsArr.forEach(function (item) {
            if (!item.name) return;
            if (!item.id) item.id = generateId();
            if (!events.find(function (e) { return e.id === item.id; })) {
                events.push(item);
                importedEvents++;
            }
        });

        saveFriends();
        saveEvents();
        closeImportModal();
        renderTagFilters();
        renderFriends();
        renderEvents();
        updateStats();
        showToast('Imported ' + imported + ' friends' + (importedEvents > 0 ? ', ' + importedEvents + ' events' : '') + '! 🎉');
    } catch (err) {
        showToast('Invalid JSON data', 'error');
    }
}

// ── Events ──────────────────────────────────────

var EVENT_TYPE_ICONS = {
    hangout: '🤝',
    birthday: '🎂',
    dating: '💕',
    party: '🎊',
    trip: '✈️',
    dinner: '🍽️',
    activity: '🎯',
    other: '📌'
};

function toggleEventsPanel() {
    document.getElementById('eventsPanel').classList.toggle('hidden');
    renderEvents();
}

function renderEvents() {
    var list = document.getElementById('eventsList');
    var empty = document.getElementById('eventsEmpty');

    var sorted = events.slice().sort(function (a, b) {
        return (a.date || '').localeCompare(b.date || '');
    });

    if (sorted.length === 0) {
        empty.classList.remove('hidden');
        list.innerHTML = '';
        return;
    }
    empty.classList.add('hidden');

    list.innerHTML = sorted.map(function (ev) {
        var icon = EVENT_TYPE_ICONS[ev.type] || '📌';
        var invited = getEventInvitedFriends(ev);
        var daysUntil = daysBetween(todayStr(), ev.date);
        var dateLabel = '';
        if (daysUntil < 0) dateLabel = 'Passed';
        else if (daysUntil === 0) dateLabel = '<strong>Today!</strong>';
        else if (daysUntil === 1) dateLabel = '<strong>Tomorrow!</strong>';
        else if (daysUntil <= 7) dateLabel = '<strong>In ' + daysUntil + ' days</strong>';
        else dateLabel = formatDate(ev.date);

        var avatarStack = '';
        if (invited.length > 0) {
            var shown = invited.slice(0, 4);
            avatarStack = '<span class="avatar-stack">' + shown.map(function (f) {
                return '<span class="mini-avatar">' + esc(getInitials(f.name)) + '</span>';
            }).join('') + '</span>';
        }

        return '<div class="event-card" onclick="openEventDetailModal(\'' + ev.id + '\')">' +
            '<div class="event-card-actions">' +
                '<button class="card-action-btn" onclick="event.stopPropagation(); openEditEvent(\'' + ev.id + '\')" title="Edit">✏️</button>' +
                '<button class="card-action-btn danger" onclick="event.stopPropagation(); deleteEvent(\'' + ev.id + '\')" title="Delete">🗑</button>' +
            '</div>' +
            '<div class="event-card-type">' + icon + '</div>' +
            '<div class="event-card-name">' + esc(ev.name) + '</div>' +
            (ev.location ? '<div class="event-card-location">📍 ' + esc(ev.location) + '</div>' : '') +
            '<div class="event-card-date">' + dateLabel + (ev.time ? ' at ' + ev.time : '') + '</div>' +
            '<div class="event-card-invited">' + avatarStack + ' ' + invited.length + ' invited</div>' +
        '</div>';
    }).join('');
}

function getEventInvitedFriends(ev) {
    var ids = {};
    (ev.invitedFriends || []).forEach(function (id) { ids[id] = true; });

    if (ev.inviteByTags && ev.inviteByTags.length > 0) {
        friends.forEach(function (f) {
            var match = ev.inviteByTags.some(function (tag) {
                return (f.tags || []).indexOf(tag) >= 0;
            });
            if (match) ids[f.id] = true;
        });
    }

    return friends.filter(function (f) { return ids[f.id]; });
}

function openEventModal() {
    document.getElementById('eventModalTitle').textContent = 'Plan an Event';
    document.getElementById('saveEventBtn').textContent = 'Create Event';
    document.getElementById('eventForm').reset();
    document.getElementById('eventId').value = '';
    document.getElementById('eventDate').value = todayStr();
    eventSelectedTags = [];
    eventSelectedFriends = [];
    renderEventTagSelector();
    renderEventFriendsChecklist();
    updateEventInvitedSummary();
    document.getElementById('eventModal').classList.remove('hidden');
}

function openEditEvent(id) {
    var ev = events.find(function (e) { return e.id === id; });
    if (!ev) return;

    document.getElementById('eventModalTitle').textContent = 'Edit Event';
    document.getElementById('saveEventBtn').textContent = 'Update Event';
    document.getElementById('eventId').value = ev.id;
    document.getElementById('eventName').value = ev.name || '';
    document.getElementById('eventType').value = ev.type || 'hangout';
    document.getElementById('eventDate').value = ev.date || '';
    document.getElementById('eventTime').value = ev.time || '';
    document.getElementById('eventLocation').value = ev.location || '';
    document.getElementById('eventDescription').value = ev.description || '';

    eventSelectedTags = (ev.inviteByTags || []).slice();
    eventSelectedFriends = (ev.invitedFriends || []).slice();
    renderEventTagSelector();
    renderEventFriendsChecklist();
    updateEventInvitedSummary();
    document.getElementById('eventModal').classList.remove('hidden');
}

function closeEventModal() {
    document.getElementById('eventModal').classList.add('hidden');
}

function saveEvent(e) {
    e.preventDefault();
    var id = document.getElementById('eventId').value;
    var isNew = !id;

    var data = {
        id: id || generateId(),
        name: document.getElementById('eventName').value.trim(),
        type: document.getElementById('eventType').value,
        date: document.getElementById('eventDate').value,
        time: document.getElementById('eventTime').value,
        location: document.getElementById('eventLocation').value.trim(),
        description: document.getElementById('eventDescription').value.trim(),
        inviteByTags: eventSelectedTags.slice(),
        invitedFriends: eventSelectedFriends.slice(),
        createdAt: todayStr()
    };

    if (isNew) {
        events.push(data);
        showToast('Event "' + data.name + '" created! 🎉');
    } else {
        var idx = events.findIndex(function (ev) { return ev.id === id; });
        if (idx >= 0) {
            data.createdAt = events[idx].createdAt || todayStr();
            events[idx] = data;
        }
        showToast('Event updated ✅');
    }

    saveEvents();
    closeEventModal();
    renderEvents();
}

function deleteEvent(id) {
    var ev = events.find(function (e) { return e.id === id; });
    if (!ev) return;
    if (!confirm('Delete event "' + ev.name + '"?')) return;

    events = events.filter(function (e) { return e.id !== id; });
    saveEvents();
    renderEvents();
    closeEventDetailModal();
    showToast('Event deleted');
}

function renderEventTagSelector() {
    var allTags = getAllTags();
    var tagNames = Object.keys(allTags).sort(function (a, b) { return allTags[b] - allTags[a]; });
    var container = document.getElementById('eventTagSelector');

    if (tagNames.length === 0) {
        container.innerHTML = '<span style="font-size:12px;opacity:0.4;">No tags yet — add tags to friends first</span>';
        return;
    }

    container.innerHTML = tagNames.map(function (tag) {
        var isActive = eventSelectedTags.indexOf(tag) >= 0;
        return '<button type="button" class="event-tag-option' + (isActive ? ' active' : '') + '" ' +
            'onclick="toggleEventTag(\'' + esc(tag.replace(/'/g, "\\'")) + '\')">' +
            esc(tag) + ' (' + allTags[tag] + ')</button>';
    }).join('');
}

function toggleEventTag(tag) {
    var idx = eventSelectedTags.indexOf(tag);
    if (idx >= 0) {
        eventSelectedTags.splice(idx, 1);
    } else {
        eventSelectedTags.push(tag);
    }
    renderEventTagSelector();
    renderEventFriendsChecklist();
    updateEventInvitedSummary();
}

function renderEventFriendsChecklist() {
    var container = document.getElementById('eventFriendsChecklist');
    var query = (document.getElementById('eventFriendSearch').value || '').toLowerCase().trim();

    var sorted = friends.slice().sort(function (a, b) { return a.name.localeCompare(b.name); });

    if (query) {
        sorted = sorted.filter(function (f) {
            return f.name.toLowerCase().includes(query) || (f.nickname || '').toLowerCase().includes(query);
        });
    }

    if (sorted.length === 0) {
        container.innerHTML = '<div style="font-size:12px;opacity:0.4;padding:8px 0;">' +
            (friends.length === 0 ? 'No friends added yet' : 'No matches') + '</div>';
        return;
    }

    container.innerHTML = sorted.map(function (f) {
        var isAutoIncluded = eventSelectedTags.length > 0 && eventSelectedTags.some(function (tag) {
            return (f.tags || []).indexOf(tag) >= 0;
        });
        var isManuallySelected = eventSelectedFriends.indexOf(f.id) >= 0;
        var isIncluded = isAutoIncluded || isManuallySelected;
        var tagsStr = (f.tags || []).slice(0, 3).join(', ');

        return '<label class="event-friend-option' + (isAutoIncluded ? ' auto-included' : '') + '">' +
            '<input type="checkbox" ' + (isIncluded ? 'checked' : '') + ' ' +
                (isAutoIncluded ? 'disabled' : '') + ' ' +
                'onchange="toggleEventFriend(\'' + f.id + '\', this.checked)">' +
            '<span class="friend-option-name">' + esc(f.name) + '</span>' +
            (tagsStr ? '<span class="friend-option-tags">' + esc(tagsStr) + '</span>' : '') +
        '</label>';
    }).join('');
}

function filterEventFriends() {
    renderEventFriendsChecklist();
}

function toggleEventFriend(friendId, checked) {
    if (checked) {
        if (eventSelectedFriends.indexOf(friendId) < 0) {
            eventSelectedFriends.push(friendId);
        }
    } else {
        eventSelectedFriends = eventSelectedFriends.filter(function (id) { return id !== friendId; });
    }
    updateEventInvitedSummary();
}

function updateEventInvitedSummary() {
    var container = document.getElementById('eventInvitedSummary');
    var total = getEventInvitedFriendsFromSelections();

    if (total.length === 0) {
        container.innerHTML = '<em style="opacity:0.5;">No friends invited yet</em>';
        return;
    }

    var names = total.slice(0, 5).map(function (f) { return f.name; }).join(', ');
    var extra = total.length > 5 ? ' and ' + (total.length - 5) + ' more' : '';
    container.innerHTML = '<strong>' + total.length + ' friend' + (total.length !== 1 ? 's' : '') + '</strong> invited: ' + esc(names) + extra;
}

function getEventInvitedFriendsFromSelections() {
    var ids = {};
    eventSelectedFriends.forEach(function (id) { ids[id] = true; });

    if (eventSelectedTags.length > 0) {
        friends.forEach(function (f) {
            var match = eventSelectedTags.some(function (tag) {
                return (f.tags || []).indexOf(tag) >= 0;
            });
            if (match) ids[f.id] = true;
        });
    }

    return friends.filter(function (f) { return ids[f.id]; });
}

function openEventDetailModal(id) {
    var ev = events.find(function (e) { return e.id === id; });
    if (!ev) return;

    var icon = EVENT_TYPE_ICONS[ev.type] || '📌';
    document.getElementById('eventDetailName').textContent = icon + ' ' + ev.name;
    var content = document.getElementById('eventDetailContent');
    var invited = getEventInvitedFriends(ev);
    var daysUntil = daysBetween(todayStr(), ev.date);

    var html = '';

    html += '<div class="detail-section"><div class="detail-section-title">Event Info</div><div class="detail-grid">';
    html += '<div class="detail-item"><div class="detail-item-label">Date</div><div class="detail-item-value">' + formatDate(ev.date) +
        (daysUntil === 0 ? ' (Today!)' : daysUntil === 1 ? ' (Tomorrow!)' : daysUntil > 0 ? ' (in ' + daysUntil + ' days)' : ' (Passed)') + '</div></div>';
    if (ev.time) html += '<div class="detail-item"><div class="detail-item-label">Time</div><div class="detail-item-value">' + esc(ev.time) + '</div></div>';
    if (ev.location) html += '<div class="detail-item"><div class="detail-item-label">📍 Location</div><div class="detail-item-value">' + esc(ev.location) + '</div></div>';
    html += '<div class="detail-item"><div class="detail-item-label">Type</div><div class="detail-item-value">' + icon + ' ' + esc(ev.type.charAt(0).toUpperCase() + ev.type.slice(1)) + '</div></div>';
    if (ev.description) {
        html += '<div class="detail-item" style="grid-column:1/-1"><div class="detail-item-label">Description</div><div class="detail-item-value" style="word-break:normal">' + esc(ev.description) + '</div></div>';
    }
    html += '</div></div>';

    if (ev.inviteByTags && ev.inviteByTags.length > 0) {
        html += '<div class="detail-section"><div class="detail-section-title">Invite Tags</div><div class="detail-tags">';
        ev.inviteByTags.forEach(function (t) {
            html += '<span class="detail-tag">' + esc(t) + '</span>';
        });
        html += '</div></div>';
    }

    html += '<div class="detail-section"><div class="detail-section-title">Invited Friends (' + invited.length + ')</div>';
    if (invited.length > 0) {
        html += '<div class="event-detail-invited-list">';
        invited.forEach(function (f) {
            var tagsStr = (f.tags || []).slice(0, 3).join(', ');
            html += '<div class="event-detail-friend">' +
                '<span class="mini-avatar">' + esc(getInitials(f.name)) + '</span>' +
                '<span class="event-detail-friend-name">' + esc(f.name) + '</span>' +
                (tagsStr ? '<span class="event-detail-friend-tags">' + esc(tagsStr) + '</span>' : '') +
            '</div>';
        });
        html += '</div>';
    } else {
        html += '<div style="opacity:0.4;font-size:13px;">No friends invited yet</div>';
    }
    html += '</div>';

    html += '<div class="detail-actions">';
    html += '<button class="btn-secondary" onclick="closeEventDetailModal(); openEditEvent(\'' + ev.id + '\')">✏️ Edit Event</button>';
    html += '<button class="btn-danger" onclick="deleteEvent(\'' + ev.id + '\')">🗑 Delete</button>';
    html += '</div>';

    content.innerHTML = html;
    document.getElementById('eventDetailModal').classList.remove('hidden');
}

function closeEventDetailModal() {
    document.getElementById('eventDetailModal').classList.add('hidden');
}

// ── Demo Data Seeding ───────────────────────────

function seedDemoData() {
    var users = getUsers();
    if (users['johndoe']) return; // already seeded

    // Create demo user
    users['johndoe'] = { password: 'johndoe', created: '2026-01-15' };
    saveUsers(users);

    // Seed demo friends
    var demoFriends = [
        {
            id: 'demo_jack_001',
            name: 'Jack',
            nickname: '',
            birthday: '1995-06-15',
            howMet: 'Gym',
            notes: 'Training partner, always spots me on bench press',
            phone: '+1 (416) 555-1234',
            email: '',
            instagram: '@jack_lifts',
            tiktok: '',
            twitter: '',
            snapchat: '',
            linkedin: '',
            otherSocial: '',
            tags: ['Best Friend', 'Gym'],
            cadence: '7',
            hangouts: [
                { id: 'h1', date: '2026-02-28', activity: 'Leg day at GoodLife', notes: '' },
                { id: 'h2', date: '2026-02-20', activity: 'Chest & back workout', notes: 'Hit a new PR on deadlift' }
            ]
        },
        {
            id: 'demo_jane_002',
            name: 'Jane Smith',
            nickname: '',
            birthday: '1997-03-22',
            howMet: 'Dating app',
            notes: 'Loves hiking and yoga',
            phone: '+1 (416) 555-5678',
            email: 'jane.smith@email.com',
            instagram: '@janesmith',
            tiktok: '',
            twitter: '',
            snapchat: '',
            linkedin: '',
            otherSocial: '',
            tags: ['Date', 'Fitness'],
            cadence: '14',
            hangouts: [
                { id: 'h3', date: '2026-02-25', activity: 'Coffee date at Balzacs', notes: 'Great conversation' }
            ]
        }
    ];

    localStorage.setItem('ft_johndoe_friends', JSON.stringify(demoFriends));
    localStorage.setItem('ft_johndoe_events', JSON.stringify([]));
}

// ── Init ────────────────────────────────────────

(function init() {
    seedDemoData();

    var savedUser = localStorage.getItem('ft_currentUser');
    if (savedUser) {
        var users = getUsers();
        if (users[savedUser]) {
            currentUser = savedUser;
            enterApp();
            return;
        }
    }
    document.getElementById('authScreen').classList.remove('hidden');
})();
