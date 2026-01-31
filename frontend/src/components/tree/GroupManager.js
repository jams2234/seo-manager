/**
 * Group Manager Component
 * Allows users to create, edit, and delete page groups
 */
import React, { useState, useEffect } from 'react';
import { groupService } from '../../services/domainService';
import './GroupManager.css';

const GroupManager = ({ domainId, onUpdate }) => {
  const [groups, setGroups] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [newGroup, setNewGroup] = useState({ name: '', color: '#3B82F6', description: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (domainId) {
      fetchGroups();
    }
  }, [domainId]);

  const fetchGroups = async () => {
    try {
      setLoading(true);
      const response = await groupService.listGroups(domainId);
      // Ensure response.data is an array before setting
      const groupsData = Array.isArray(response.data) ? response.data : [];
      setGroups(groupsData);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch groups:', err);
      setError('그룹 목록을 불러오는데 실패했습니다.');
      setGroups([]); // Ensure groups is array even on error
    } finally {
      setLoading(false);
    }
  };

  const createGroup = async () => {
    if (!newGroup.name.trim()) {
      alert('그룹 이름을 입력해주세요.');
      return;
    }

    try {
      setLoading(true);
      const groupData = {
        domain: Number(domainId), // Convert to integer
        name: newGroup.name.trim(),
        color: newGroup.color,
        description: newGroup.description || ''
      };

      console.log('Creating group with data:', groupData);
      await groupService.createGroup(groupData);

      await fetchGroups();
      setShowCreateForm(false);
      setNewGroup({ name: '', color: '#3B82F6', description: '' });
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error('Failed to create group:', err);
      console.error('Error response:', err.response?.data);

      // Display detailed error message
      let errorMsg = '그룹 생성 실패: ';
      if (err.response?.data) {
        // Django validation errors
        if (err.response.data.name) {
          errorMsg += '이름: ' + err.response.data.name.join(', ');
        } else if (err.response.data.domain) {
          errorMsg += '도메인: ' + err.response.data.domain.join(', ');
        } else if (err.response.data.non_field_errors) {
          errorMsg += err.response.data.non_field_errors.join(', ');
        } else if (err.response.data.error) {
          errorMsg += err.response.data.error;
        } else {
          errorMsg += JSON.stringify(err.response.data);
        }
      } else {
        errorMsg += err.message;
      }

      alert(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const updateGroup = async () => {
    if (!editingGroup.name.trim()) {
      alert('그룹 이름을 입력해주세요.');
      return;
    }

    try {
      setLoading(true);
      const updateData = {
        name: editingGroup.name.trim(),
        color: editingGroup.color,
        description: editingGroup.description || ''
      };

      console.log('Updating group with data:', updateData);
      await groupService.updateGroup(editingGroup.id, updateData);

      await fetchGroups();
      setEditingGroup(null);
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error('Failed to update group:', err);
      console.error('Error response:', err.response?.data);

      let errorMsg = '그룹 수정 실패: ';
      if (err.response?.data) {
        if (err.response.data.name) {
          errorMsg += '이름: ' + err.response.data.name.join(', ');
        } else if (err.response.data.non_field_errors) {
          errorMsg += err.response.data.non_field_errors.join(', ');
        } else if (err.response.data.error) {
          errorMsg += err.response.data.error;
        } else {
          errorMsg += JSON.stringify(err.response.data);
        }
      } else {
        errorMsg += err.message;
      }

      alert(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const deleteGroup = async (groupId) => {
    const confirmed = window.confirm('이 그룹을 삭제하시겠습니까? 그룹에 속한 페이지는 그룹이 해제됩니다.');
    if (!confirmed) return;

    try {
      setLoading(true);
      await groupService.deleteGroup(groupId);
      await fetchGroups();
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error('Failed to delete group:', err);
      alert('그룹 삭제 실패: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const cancelEdit = () => {
    setEditingGroup(null);
    setShowCreateForm(false);
    setNewGroup({ name: '', color: '#3B82F6', description: '' });
  };

  if (loading && groups.length === 0) {
    return <div className="group-manager loading">로딩 중...</div>;
  }

  return (
    <div className="group-manager">
      <div className="group-manager-header">
        <h3>📁 페이지 그룹</h3>
        {!showCreateForm && !editingGroup && (
          <button
            className="btn-create-group"
            onClick={() => setShowCreateForm(true)}
            disabled={loading}
          >
            + 새 그룹
          </button>
        )}
      </div>

      {error && (
        <div className="group-error">{error}</div>
      )}

      {/* Group List */}
      <div className="group-list">
        {Array.isArray(groups) && groups.map(group => (
          <div key={group.id} className="group-item">
            {editingGroup && editingGroup.id === group.id ? (
              // Edit mode
              <div className="group-edit-form">
                <input
                  type="text"
                  className="group-name-input"
                  value={editingGroup.name}
                  onChange={(e) => setEditingGroup({ ...editingGroup, name: e.target.value })}
                  placeholder="그룹 이름"
                />
                <input
                  type="color"
                  className="group-color-input"
                  value={editingGroup.color}
                  onChange={(e) => setEditingGroup({ ...editingGroup, color: e.target.value })}
                />
                <input
                  type="text"
                  className="group-description-input"
                  value={editingGroup.description || ''}
                  onChange={(e) => setEditingGroup({ ...editingGroup, description: e.target.value })}
                  placeholder="설명 (선택사항)"
                />
                <div className="group-edit-actions">
                  <button className="btn-save" onClick={updateGroup} disabled={loading}>
                    💾 저장
                  </button>
                  <button className="btn-cancel" onClick={cancelEdit} disabled={loading}>
                    ❌ 취소
                  </button>
                </div>
              </div>
            ) : (
              // View mode
              <>
                <div
                  className="group-color-badge"
                  style={{ backgroundColor: group.color }}
                  title={group.color}
                />
                <div className="group-info">
                  <div className="group-name">{group.name}</div>
                  {group.description && (
                    <div className="group-description">{group.description}</div>
                  )}
                  <div className="group-count">
                    {group.page_count || 0} 페이지
                  </div>
                </div>
                <div className="group-actions">
                  <button
                    className="btn-edit-group"
                    onClick={() => setEditingGroup({ ...group })}
                    title="편집"
                  >
                    ✏️
                  </button>
                  <button
                    className="btn-delete-group"
                    onClick={() => deleteGroup(group.id)}
                    title="삭제"
                  >
                    🗑️
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      {/* Create Form */}
      {showCreateForm && (
        <div className="group-create-form">
          <h4>새 그룹 만들기</h4>
          <input
            type="text"
            className="group-name-input"
            placeholder="그룹 이름"
            value={newGroup.name}
            onChange={(e) => setNewGroup({ ...newGroup, name: e.target.value })}
          />
          <div className="color-input-wrapper">
            <label>색상:</label>
            <input
              type="color"
              className="group-color-input"
              value={newGroup.color}
              onChange={(e) => setNewGroup({ ...newGroup, color: e.target.value })}
            />
            <span className="color-preview" style={{ backgroundColor: newGroup.color }}>
              {newGroup.color}
            </span>
          </div>
          <input
            type="text"
            className="group-description-input"
            placeholder="설명 (선택사항)"
            value={newGroup.description}
            onChange={(e) => setNewGroup({ ...newGroup, description: e.target.value })}
          />
          <div className="group-form-actions">
            <button className="btn-create" onClick={createGroup} disabled={loading}>
              ✅ 생성
            </button>
            <button className="btn-cancel" onClick={cancelEdit} disabled={loading}>
              ❌ 취소
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default GroupManager;
