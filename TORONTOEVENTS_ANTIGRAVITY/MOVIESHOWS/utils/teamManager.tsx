/**
 * UPDATE #110: Team Management System
 * Manage team subscriptions and permissions
 */

type TeamRole = 'owner' | 'admin' | 'member';

interface TeamMember {
    id: string;
    userId: number;
    teamId: string;
    role: TeamRole;
    email: string;
    name?: string;
    joinedAt: string;
    lastActiveAt?: string;
}

interface Team {
    id: string;
    name: string;
    ownerId: number;
    subscriptionId: string;
    maxMembers: number;
    currentMembers: number;
    createdAt: string;
    settings: {
        allowMemberInvites: boolean;
        requireApproval: boolean;
    };
}

interface TeamInvitation {
    id: string;
    teamId: string;
    email: string;
    role: TeamRole;
    invitedBy: number;
    status: 'pending' | 'accepted' | 'declined' | 'expired';
    createdAt: string;
    expiresAt: string;
    token: string;
}

class TeamManager {
    private teams: Map<string, Team> = new Map();
    private members: Map<string, TeamMember> = new Map();
    private invitations: TeamInvitation[] = [];

    /**
     * Create team
     */
    createTeam(ownerId: number, name: string, subscriptionId: string, maxMembers: number): Team {
        const team: Team = {
            id: `team_${Date.now()}`,
            name,
            ownerId,
            subscriptionId,
            maxMembers,
            currentMembers: 1,
            createdAt: new Date().toISOString(),
            settings: {
                allowMemberInvites: false,
                requireApproval: true
            }
        };

        this.teams.set(team.id, team);

        // Add owner as first member
        this.addMember(team.id, ownerId, 'owner', `owner${ownerId}@example.com`);

        return team;
    }

    /**
     * Add team member
     */
    addMember(teamId: string, userId: number, role: TeamRole, email: string): TeamMember {
        const team = this.teams.get(teamId);
        if (!team) throw new Error('Team not found');

        if (team.currentMembers >= team.maxMembers) {
            throw new Error('Team is at maximum capacity');
        }

        const member: TeamMember = {
            id: `member_${Date.now()}`,
            userId,
            teamId,
            role,
            email,
            joinedAt: new Date().toISOString()
        };

        this.members.set(member.id, member);
        team.currentMembers++;

        return member;
    }

    /**
     * Invite team member
     */
    inviteMember(teamId: string, email: string, role: TeamRole, invitedBy: number): TeamInvitation {
        const team = this.teams.get(teamId);
        if (!team) throw new Error('Team not found');

        // Check if inviter has permission
        const inviter = this.getTeamMembers(teamId).find(m => m.userId === invitedBy);
        if (!inviter || (inviter.role === 'member' && !team.settings.allowMemberInvites)) {
            throw new Error('No permission to invite members');
        }

        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + 7); // Invitations expire in 7 days

        const invitation: TeamInvitation = {
            id: `inv_${Date.now()}`,
            teamId,
            email,
            role,
            invitedBy,
            status: 'pending',
            createdAt: new Date().toISOString(),
            expiresAt: expiresAt.toISOString(),
            token: this.generateInviteToken()
        };

        this.invitations.push(invitation);
        return invitation;
    }

    /**
     * Accept invitation
     */
    acceptInvitation(token: string, userId: number): TeamMember {
        const invitation = this.invitations.find(inv => inv.token === token);

        if (!invitation) {
            throw new Error('Invalid invitation');
        }

        if (invitation.status !== 'pending') {
            throw new Error('Invitation already processed');
        }

        if (new Date() > new Date(invitation.expiresAt)) {
            invitation.status = 'expired';
            throw new Error('Invitation has expired');
        }

        invitation.status = 'accepted';

        return this.addMember(invitation.teamId, userId, invitation.role, invitation.email);
    }

    /**
     * Remove team member
     */
    removeMember(teamId: string, memberId: string, removedBy: number): void {
        const team = this.teams.get(teamId);
        if (!team) throw new Error('Team not found');

        const remover = this.getTeamMembers(teamId).find(m => m.userId === removedBy);
        if (!remover || (remover.role !== 'owner' && remover.role !== 'admin')) {
            throw new Error('No permission to remove members');
        }

        const member = this.members.get(memberId);
        if (!member) throw new Error('Member not found');

        if (member.role === 'owner') {
            throw new Error('Cannot remove team owner');
        }

        this.members.delete(memberId);
        team.currentMembers--;
    }

    /**
     * Update member role
     */
    updateMemberRole(teamId: string, memberId: string, newRole: TeamRole, updatedBy: number): void {
        const team = this.teams.get(teamId);
        if (!team) throw new Error('Team not found');

        const updater = this.getTeamMembers(teamId).find(m => m.userId === updatedBy);
        if (!updater || updater.role !== 'owner') {
            throw new Error('Only team owner can update roles');
        }

        const member = this.members.get(memberId);
        if (!member) throw new Error('Member not found');

        if (member.role === 'owner') {
            throw new Error('Cannot change owner role');
        }

        member.role = newRole;
    }

    /**
     * Get team members
     */
    getTeamMembers(teamId: string): TeamMember[] {
        return Array.from(this.members.values()).filter(m => m.teamId === teamId);
    }

    /**
     * Get user's teams
     */
    getUserTeams(userId: number): Team[] {
        const userMemberships = Array.from(this.members.values()).filter(m => m.userId === userId);
        return userMemberships.map(m => this.teams.get(m.teamId)!).filter(Boolean);
    }

    /**
     * Get team
     */
    getTeam(teamId: string): Team | undefined {
        return this.teams.get(teamId);
    }

    private generateInviteToken(): string {
        return `inv_${Math.random().toString(36).substr(2, 16)}`;
    }
}

export const teamManager = new TeamManager();

/**
 * Team management component
 */
import React from 'react';

interface TeamManagementProps {
    teamId: string;
    currentUserId: number;
}

export function TeamManagement({ teamId, currentUserId }: TeamManagementProps) {
    const team = teamManager.getTeam(teamId);
    const members = teamManager.getTeamMembers(teamId);
    const currentMember = members.find(m => m.userId === currentUserId);

    if (!team || !currentMember) {
        return <div>Team not found</div>;
    }

    const canManageMembers = currentMember.role === 'owner' || currentMember.role === 'admin';

    return (
        <div className="team-management">
            <div className="team-header">
                <h2>{team.name}</h2>
                <span className="member-count">
                    {team.currentMembers} / {team.maxMembers} members
                </span>
            </div>

            <div className="members-list">
                <h3>Team Members</h3>
                {members.map(member => (
                    <div key={member.id} className="member-row">
                        <div className="member-info">
                            <div className="member-email">{member.email}</div>
                            <span className={`member-role role-${member.role}`}>
                                {member.role}
                            </span>
                        </div>
                        {canManageMembers && member.role !== 'owner' && (
                            <button
                                onClick={() => teamManager.removeMember(teamId, member.id, currentUserId)}
                                className="remove-button"
                            >
                                Remove
                            </button>
                        )}
                    </div>
                ))}
            </div>

            {canManageMembers && team.currentMembers < team.maxMembers && (
                <div className="invite-section">
                    <h3>Invite Members</h3>
                    <p>Invite new members to join your team</p>
                    {/* Invite form would go here */}
                </div>
            )}
        </div>
    );
}

const styles = `
.team-management {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

.team-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.team-header h2 {
  margin: 0;
}

.member-count {
  padding: 0.5rem 1rem;
  background: rgba(102, 126, 234, 0.2);
  border-radius: 6px;
  font-weight: 600;
}

.members-list h3 {
  margin: 0 0 1rem;
}

.member-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  margin-bottom: 0.75rem;
}

.member-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.member-email {
  font-weight: 500;
}

.member-role {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: capitalize;
}

.role-owner {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
}

.role-admin {
  background: rgba(102, 126, 234, 0.2);
  color: #667eea;
}

.role-member {
  background: rgba(148, 163, 184, 0.2);
  color: #94a3b8;
}

.remove-button {
  padding: 0.5rem 1rem;
  background: rgba(248, 113, 113, 0.2);
  border: 1px solid rgba(248, 113, 113, 0.3);
  border-radius: 6px;
  color: #f87171;
  cursor: pointer;
  transition: all 0.2s;
}

.remove-button:hover {
  background: rgba(248, 113, 113, 0.3);
}

.invite-section {
  margin-top: 2rem;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
}

.invite-section h3 {
  margin: 0 0 0.5rem;
}

.invite-section p {
  margin: 0 0 1rem;
  opacity: 0.8;
}
`;
