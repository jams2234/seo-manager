/**
 * Category Manager Component
 * Manages page group categories with hierarchical organization
 */
import React, { useState, useEffect } from 'react';
import { categoryService, groupService } from '../../services/domainService';
import './CategoryManager.css';

const CategoryManager = ({ domainId, onUpdate }) => {
  const [categories, setCategories] = useState([]);
  const [showCreateCategoryForm, setShowCreateCategoryForm] = useState(false);
  const [showCreateGroupForm, setShowCreateGroupForm] = useState(null); // categoryId
  const [editingCategory, setEditingCategory] = useState(null);
  const [editingGroup, setEditingGroup] = useState(null);
  const [newCategory, setNewCategory] = useState({
    name: '',
    icon: '📁',
    description: ''
  });
  const [newGroup, setNewGroup] = useState({
    name: '',
    color: '#3B82F6',
    description: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (domainId) {
      fetchCategoriesWithGroups();
    }
  }, [domainId]);

  const fetchCategoriesWithGroups = async () => {
    try {
      setLoading(true);
      const categoriesResponse = await categoryService.listCategories(domainId);
      const categoriesData = Array.isArray(categoriesResponse.data)
        ? categoriesResponse.data
        : [];

      // Fetch groups for each category
      const categoriesWithGroups = await Promise.all(
        categoriesData.map(async (category) => {
          try {
            const groupsResponse = await categoryService.getCategoryGroups(category.id);
            return {
              ...category,
              groups: Array.isArray(groupsResponse.data) ? groupsResponse.data : []
            };
          } catch (err) {
            console.error(`Failed to fetch groups for category ${category.id}:`, err);
            return { ...category, groups: [] };
          }
        })
      );

      // Also fetch uncategorized groups
      const uncategorizedResponse = await groupService.listGroups(domainId, 'null');
      const uncategorizedGroups = Array.isArray(uncategorizedResponse.data)
        ? uncategorizedResponse.data
        : [];

      if (uncategorizedGroups.length > 0) {
        categoriesWithGroups.push({
          id: 'uncategorized',
          name: '카테고리 없음',
          icon: '📂',
          domain: domainId,
          groups: uncategorizedGroups,
          group_count: uncategorizedGroups.length,
          page_count: uncategorizedGroups.reduce((sum, g) => sum + (g.page_count || 0), 0),
          is_expanded: true
        });
      }

      setCategories(categoriesWithGroups);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch categories:', err);
      setError('카테고리를 불러오는데 실패했습니다.');
      setCategories([]);
    } finally {
      setLoading(false);
    }
  };

  const createCategory = async () => {
    if (!newCategory.name.trim()) {
      alert('카테고리 이름을 입력해주세요.');
      return;
    }

    try {
      setLoading(true);
      const categoryData = {
        domain: Number(domainId),
        name: newCategory.name.trim(),
        icon: newCategory.icon || '📁',
        description: newCategory.description || ''
      };

      await categoryService.createCategory(categoryData);
      await fetchCategoriesWithGroups();
      setShowCreateCategoryForm(false);
      setNewCategory({ name: '', icon: '📁', description: '' });
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error('Failed to create category:', err);
      alert('카테고리 생성 실패: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const updateCategory = async () => {
    if (!editingCategory.name.trim()) {
      alert('카테고리 이름을 입력해주세요.');
      return;
    }

    try {
      setLoading(true);
      await categoryService.updateCategory(editingCategory.id, {
        name: editingCategory.name.trim(),
        icon: editingCategory.icon,
        description: editingCategory.description || ''
      });
      await fetchCategoriesWithGroups();
      setEditingCategory(null);
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error('Failed to update category:', err);
      alert('카테고리 수정 실패: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const deleteCategory = async (categoryId) => {
    const confirmed = window.confirm(
      '이 카테고리를 삭제하시겠습니까? 카테고리에 속한 그룹은 "카테고리 없음"으로 이동합니다.'
    );
    if (!confirmed) return;

    try {
      setLoading(true);
      await categoryService.deleteCategory(categoryId);
      await fetchCategoriesWithGroups();
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error('Failed to delete category:', err);
      alert('카테고리 삭제 실패: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const toggleCategory = async (categoryId) => {
    if (categoryId === 'uncategorized') {
      // Local state for uncategorized
      setCategories(cats =>
        cats.map(cat =>
          cat.id === 'uncategorized'
            ? { ...cat, is_expanded: !cat.is_expanded }
            : cat
        )
      );
    } else {
      try {
        await categoryService.toggleExpand(categoryId);
        setCategories(cats =>
          cats.map(cat =>
            cat.id === categoryId
              ? { ...cat, is_expanded: !cat.is_expanded }
              : cat
          )
        );
      } catch (err) {
        console.error('Failed to toggle category:', err);
      }
    }
  };

  const createGroupInCategory = async (categoryId) => {
    if (!newGroup.name.trim()) {
      alert('그룹 이름을 입력해주세요.');
      return;
    }

    try {
      setLoading(true);
      const groupData = {
        domain: Number(domainId),
        category: categoryId === 'uncategorized' ? null : Number(categoryId),
        name: newGroup.name.trim(),
        color: newGroup.color,
        description: newGroup.description || ''
      };

      await groupService.createGroup(groupData);
      await fetchCategoriesWithGroups();
      setShowCreateGroupForm(null);
      setNewGroup({ name: '', color: '#3B82F6', description: '' });
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error('Failed to create group:', err);
      alert('그룹 생성 실패: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const deleteGroup = async (groupId) => {
    const confirmed = window.confirm('이 그룹을 삭제하시겠습니까?');
    if (!confirmed) return;

    try {
      setLoading(true);
      await groupService.deleteGroup(groupId);
      await fetchCategoriesWithGroups();
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error('Failed to delete group:', err);
      alert('그룹 삭제 실패: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const cancelEdit = () => {
    setEditingCategory(null);
    setEditingGroup(null);
    setShowCreateCategoryForm(false);
    setShowCreateGroupForm(null);
    setNewCategory({ name: '', icon: '📁', description: '' });
    setNewGroup({ name: '', color: '#3B82F6', description: '' });
  };

  if (loading && categories.length === 0) {
    return <div className="category-manager loading">로딩 중...</div>;
  }

  return (
    <div className="category-manager">
      <div className="category-manager-header">
        <h3>📁 카테고리 & 그룹</h3>
        {!showCreateCategoryForm && (
          <button
            className="btn-create-category"
            onClick={() => setShowCreateCategoryForm(true)}
            disabled={loading}
          >
            + 새 카테고리
          </button>
        )}
      </div>

      {error && <div className="category-error">{error}</div>}

      {/* Create Category Form */}
      {showCreateCategoryForm && (
        <div className="category-create-form">
          <h4>새 카테고리 만들기</h4>
          <div className="form-row">
            <input
              type="text"
              placeholder="아이콘 (예: 📁)"
              value={newCategory.icon}
              onChange={(e) => setNewCategory({ ...newCategory, icon: e.target.value })}
              maxLength="10"
              className="category-icon-input"
            />
            <input
              type="text"
              placeholder="카테고리 이름"
              value={newCategory.name}
              onChange={(e) => setNewCategory({ ...newCategory, name: e.target.value })}
              className="category-name-input"
            />
          </div>
          <input
            type="text"
            placeholder="설명 (선택사항)"
            value={newCategory.description}
            onChange={(e) => setNewCategory({ ...newCategory, description: e.target.value })}
            className="category-description-input"
          />
          <div className="form-actions">
            <button className="btn-create" onClick={createCategory} disabled={loading}>
              ✅ 생성
            </button>
            <button className="btn-cancel" onClick={cancelEdit} disabled={loading}>
              ❌ 취소
            </button>
          </div>
        </div>
      )}

      {/* Category List */}
      <div className="category-list">
        {Array.isArray(categories) &&
          categories.map((category) => (
            <div key={category.id} className="category-item">
              <div className="category-header">
                <button
                  className="category-expand-btn"
                  onClick={() => toggleCategory(category.id)}
                >
                  {category.is_expanded ? '▼' : '▶'}
                </button>

                <span className="category-icon">{category.icon}</span>

                {editingCategory && editingCategory.id === category.id ? (
                  <input
                    type="text"
                    value={editingCategory.name}
                    onChange={(e) =>
                      setEditingCategory({ ...editingCategory, name: e.target.value })
                    }
                    className="category-name-input-inline"
                  />
                ) : (
                  <span className="category-name">{category.name}</span>
                )}

                <span className="category-stats">
                  {category.group_count || 0}그룹 · {category.page_count || 0}페이지
                </span>

                {category.id !== 'uncategorized' && (
                  <div className="category-actions">
                    {editingCategory && editingCategory.id === category.id ? (
                      <>
                        <button
                          className="btn-save-sm"
                          onClick={updateCategory}
                          disabled={loading}
                        >
                          💾
                        </button>
                        <button className="btn-cancel-sm" onClick={cancelEdit} disabled={loading}>
                          ❌
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          className="btn-edit-sm"
                          onClick={() => setEditingCategory({ ...category })}
                        >
                          ✏️
                        </button>
                        <button
                          className="btn-delete-sm"
                          onClick={() => deleteCategory(category.id)}
                        >
                          🗑️
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* Groups in Category */}
              {category.is_expanded && (
                <div className="category-groups">
                  {category.groups && category.groups.length > 0 ? (
                    category.groups.map((group) => (
                      <div key={group.id} className="group-item-compact">
                        <div
                          className="group-color-dot"
                          style={{ backgroundColor: group.color }}
                        />
                        <span className="group-name">{group.name}</span>
                        <span className="group-stats">
                          {group.page_count || 0}페이지
                          {group.avg_seo_score && ` · SEO ${group.avg_seo_score}`}
                        </span>
                        <button
                          className="btn-delete-sm"
                          onClick={() => deleteGroup(group.id)}
                          title="그룹 삭제"
                        >
                          🗑️
                        </button>
                      </div>
                    ))
                  ) : (
                    <div className="empty-groups">그룹이 없습니다</div>
                  )}

                  {/* Create Group in Category */}
                  {showCreateGroupForm === category.id ? (
                    <div className="group-create-form-inline">
                      <input
                        type="color"
                        value={newGroup.color}
                        onChange={(e) => setNewGroup({ ...newGroup, color: e.target.value })}
                        className="group-color-input-sm"
                      />
                      <input
                        type="text"
                        placeholder="그룹 이름"
                        value={newGroup.name}
                        onChange={(e) => setNewGroup({ ...newGroup, name: e.target.value })}
                        className="group-name-input-inline"
                      />
                      <button
                        className="btn-save-sm"
                        onClick={() => createGroupInCategory(category.id)}
                        disabled={loading}
                      >
                        ✅
                      </button>
                      <button className="btn-cancel-sm" onClick={cancelEdit} disabled={loading}>
                        ❌
                      </button>
                    </div>
                  ) : (
                    <button
                      className="btn-add-group"
                      onClick={() => setShowCreateGroupForm(category.id)}
                    >
                      + 그룹 추가
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
      </div>
    </div>
  );
};

export default CategoryManager;
