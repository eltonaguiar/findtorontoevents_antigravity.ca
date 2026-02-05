import { useState, useEffect, useCallback } from "react";
import { getAuthBase } from "../utils/auth";
import { fcApiFetch } from "../utils/apiLog";

interface LinkList {
  id: number;
  list_name: string;
  links: string;
  created_at: string;
  updated_at: string;
}

interface MyLinkListsProps {
  userId: number;
}

export default function MyLinkLists({ userId }: MyLinkListsProps) {
  const [lists, setLists] = useState<LinkList[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [editingList, setEditingList] = useState<LinkList | null>(null);
  const [newListName, setNewListName] = useState("");
  const [newListLinks, setNewListLinks] = useState("");
  const [showNewForm, setShowNewForm] = useState(false);
  const [selectedListId, setSelectedListId] = useState<number | null>(null);

  const fetchLists = useCallback(async () => {
    setLoading(true);
    try {
      const base = getAuthBase();
      if (!base) return;
      const res = await fcApiFetch(`${base}/get_link_lists.php?user_id=${userId}`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.lists)) {
          setLists(data.lists);
        }
      }
    } catch (e) {
      console.error("Failed to fetch link lists", e);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (expanded && lists.length === 0) {
      fetchLists();
    }
  }, [expanded, lists.length, fetchLists]);

  const handleSaveList = async (listName: string, links: string) => {
    try {
      const base = getAuthBase();
      if (!base) return;
      const res = await fcApiFetch(`${base}/save_link_list.php`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, list_name: listName, links }),
      });
      const data = await res.json();
      if (data.status === "success") {
        await fetchLists();
        setEditingList(null);
        setShowNewForm(false);
        setNewListName("");
        setNewListLinks("");
      } else {
        alert("Failed to save: " + (data.error || "Unknown error"));
      }
    } catch (e) {
      alert("Error saving list: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  const handleDeleteList = async (listId: number) => {
    if (!confirm("Delete this list?")) return;
    try {
      const base = getAuthBase();
      if (!base) return;
      const res = await fcApiFetch(`${base}/delete_link_list.php`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, id: listId }),
      });
      const data = await res.json();
      if (data.status === "success") {
        setLists((prev) => prev.filter((l) => l.id !== listId));
        if (selectedListId === listId) setSelectedListId(null);
      } else {
        alert("Failed to delete: " + (data.error || "Unknown error"));
      }
    } catch (e) {
      alert("Error deleting list: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  const selectedList = lists.find((l) => l.id === selectedListId);

  return (
    <div
      style={{
        marginBottom: "1.5rem",
        background: "var(--card-bg)",
        borderRadius: "12px",
        border: "1px solid var(--glass-border)",
        overflow: "hidden",
      }}
    >
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        style={{
          width: "100%",
          padding: "12px 16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "rgba(255,255,255,0.04)",
          border: "none",
          color: "inherit",
          cursor: "pointer",
          fontSize: "1rem",
          fontWeight: 600,
        }}
      >
        <span>My Favourite Creator Content</span>
        <span style={{ opacity: 0.6 }}>{expanded ? "▼" : "▶"}</span>
      </button>

      {expanded && (
        <div style={{ padding: "16px" }}>
          {loading && lists.length === 0 ? (
            <div style={{ color: "var(--text-muted)" }}>Loading...</div>
          ) : (
            <>
              {/* List selector */}
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "12px" }}>
                {lists.map((list) => (
                  <button
                    key={list.id}
                    type="button"
                    onClick={() => setSelectedListId(list.id === selectedListId ? null : list.id)}
                    style={{
                      padding: "8px 14px",
                      borderRadius: "8px",
                      border: list.id === selectedListId ? "2px solid var(--accent)" : "1px solid rgba(255,255,255,0.2)",
                      background: list.id === selectedListId ? "rgba(var(--accent-rgb), 0.2)" : "rgba(255,255,255,0.05)",
                      color: "inherit",
                      cursor: "pointer",
                      fontSize: "0.9rem",
                    }}
                  >
                    {list.list_name}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => {
                    setShowNewForm(true);
                    setEditingList(null);
                    setSelectedListId(null);
                  }}
                  style={{
                    padding: "8px 14px",
                    borderRadius: "8px",
                    border: "1px dashed rgba(255,255,255,0.3)",
                    background: "transparent",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    fontSize: "0.9rem",
                  }}
                >
                  + New List
                </button>
              </div>

              {/* New list form */}
              {showNewForm && !editingList && (
                <div
                  style={{
                    padding: "12px",
                    background: "rgba(255,255,255,0.03)",
                    borderRadius: "8px",
                    marginBottom: "12px",
                  }}
                >
                  <div style={{ marginBottom: "8px", fontWeight: 500 }}>Create New List</div>
                  <input
                    type="text"
                    value={newListName}
                    onChange={(e) => setNewListName(e.target.value)}
                    placeholder="List name (e.g., My Cheer Up List)"
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      marginBottom: "8px",
                      background: "rgba(255,255,255,0.06)",
                      border: "1px solid rgba(255,255,255,0.15)",
                      borderRadius: "6px",
                      color: "inherit",
                      fontSize: "0.9rem",
                    }}
                  />
                  <textarea
                    value={newListLinks}
                    onChange={(e) => setNewListLinks(e.target.value)}
                    placeholder={"Paste links here, one per line:\nhttps://youtube.com/watch?v=...\nhttps://tiktok.com/@user/video/..."}
                    rows={5}
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      background: "rgba(255,255,255,0.06)",
                      border: "1px solid rgba(255,255,255,0.15)",
                      borderRadius: "6px",
                      color: "inherit",
                      fontSize: "0.85rem",
                      resize: "vertical",
                    }}
                  />
                  <div style={{ display: "flex", gap: "8px", marginTop: "10px" }}>
                    <button
                      type="button"
                      onClick={() => {
                        if (!newListName.trim()) {
                          alert("Please enter a list name");
                          return;
                        }
                        handleSaveList(newListName.trim(), newListLinks);
                      }}
                      style={{
                        padding: "8px 16px",
                        background: "rgba(34, 197, 94, 0.2)",
                        border: "1px solid rgba(34, 197, 94, 0.4)",
                        borderRadius: "6px",
                        color: "#86efac",
                        cursor: "pointer",
                        fontSize: "0.85rem",
                      }}
                    >
                      Save List
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setShowNewForm(false);
                        setNewListName("");
                        setNewListLinks("");
                      }}
                      style={{
                        padding: "8px 16px",
                        background: "rgba(255,255,255,0.1)",
                        border: "1px solid rgba(255,255,255,0.2)",
                        borderRadius: "6px",
                        color: "white",
                        cursor: "pointer",
                        fontSize: "0.85rem",
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {/* Selected list view */}
              {selectedList && !editingList && (
                <div
                  style={{
                    padding: "12px",
                    background: "rgba(255,255,255,0.03)",
                    borderRadius: "8px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                    <div style={{ fontWeight: 600, fontSize: "1rem" }}>{selectedList.list_name}</div>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button
                        type="button"
                        onClick={() => setEditingList(selectedList)}
                        style={{
                          padding: "6px 12px",
                          background: "rgba(255,255,255,0.1)",
                          border: "1px solid rgba(255,255,255,0.2)",
                          borderRadius: "6px",
                          color: "white",
                          cursor: "pointer",
                          fontSize: "0.8rem",
                        }}
                      >
                        ✏️ Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteList(selectedList.id)}
                        style={{
                          padding: "6px 12px",
                          background: "rgba(239, 68, 68, 0.15)",
                          border: "1px solid rgba(239, 68, 68, 0.3)",
                          borderRadius: "6px",
                          color: "#fca5a5",
                          cursor: "pointer",
                          fontSize: "0.8rem",
                        }}
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {selectedList.links
                      .split(/\r?\n/)
                      .map((line) => line.trim())
                      .filter(Boolean)
                      .map((link, i) => (
                        <a
                          key={i}
                          href={link}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: "block",
                            padding: "8px 12px",
                            background: "rgba(255,255,255,0.05)",
                            borderRadius: "6px",
                            color: "#7dd3fc",
                            textDecoration: "none",
                            fontSize: "0.85rem",
                            wordBreak: "break-all",
                            transition: "background 0.15s",
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.1)")}
                          onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
                        >
                          {link}
                        </a>
                      ))}
                    {!selectedList.links.trim() && (
                      <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                        No links yet. Click Edit to add some!
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Edit list form */}
              {editingList && (
                <div
                  style={{
                    padding: "12px",
                    background: "rgba(255,255,255,0.03)",
                    borderRadius: "8px",
                  }}
                >
                  <div style={{ marginBottom: "8px", fontWeight: 500 }}>
                    Editing: {editingList.list_name}
                  </div>
                  <textarea
                    defaultValue={editingList.links}
                    id={`edit-links-${editingList.id}`}
                    placeholder="Paste links here, one per line"
                    rows={8}
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      background: "rgba(255,255,255,0.06)",
                      border: "1px solid rgba(255,255,255,0.15)",
                      borderRadius: "6px",
                      color: "inherit",
                      fontSize: "0.85rem",
                      resize: "vertical",
                    }}
                  />
                  <div style={{ display: "flex", gap: "8px", marginTop: "10px" }}>
                    <button
                      type="button"
                      onClick={() => {
                        const textarea = document.getElementById(`edit-links-${editingList.id}`) as HTMLTextAreaElement;
                        handleSaveList(editingList.list_name, textarea?.value || "");
                      }}
                      style={{
                        padding: "8px 16px",
                        background: "rgba(34, 197, 94, 0.2)",
                        border: "1px solid rgba(34, 197, 94, 0.4)",
                        borderRadius: "6px",
                        color: "#86efac",
                        cursor: "pointer",
                        fontSize: "0.85rem",
                      }}
                    >
                      💾 Save Changes
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingList(null)}
                      style={{
                        padding: "8px 16px",
                        background: "rgba(255,255,255,0.1)",
                        border: "1px solid rgba(255,255,255,0.2)",
                        borderRadius: "6px",
                        color: "white",
                        cursor: "pointer",
                        fontSize: "0.85rem",
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {lists.length === 0 && !showNewForm && (
                <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                  No lists yet. Create your first list to save your favourite content links!
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
