/**
 * Category Manager Component
 * Manages page group categories with hierarchical organization
 * Shows pages within groups and supports group-based filtering
 */
import React, { useState, useEffect } from 'react';
import { categoryService, groupService, pageService } from '../../services/domainService';
import { getRandomGroupColor } from '../../utils/colorUtils';
import './CategoryManager.css';

const CategoryManager = ({ domainId, onUpdate, onGroupFilter, activeGroupFilter }) => {
  const [categories, setCategories] = useState([]);
  const [showCreateCategoryForm, setShowCreateCategoryForm] = useState(false);
  const [showCreateGroupForm, setShowCreateGroupForm] = useState(null); // categoryId
  const [editingCategory, setEditingCategory] = useState(null);
  const [expandedGroups, setExpandedGroups] = useState({}); // Track which groups show pages
  const [groupPages, setGroupPages] = useState({}); // Cache pages for each group
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

      // First, fetch all groups for this domain (without category filter)
      const allGroupsResponse = await groupService.listGroups(domainId);
      const allGroups = Array.isArray(allGroupsResponse.data?.results)
        ? allGroupsResponse.data.results
        : Array.isArray(allGroupsResponse.data)
          ? allGroupsResponse.data
          : [];

      // Fetch categories
      const categoriesResponse = await categoryService.listCategories(domainId);
      const categoriesData = Array.isArray(categoriesResponse.data?.results)
        ? categoriesResponse.data.results
        : Array.isArray(categoriesResponse.data)
          ? categoriesResponse.data
          : [];

      // Group the fetched groups by category
      const groupsByCategory = {};
      const uncategorizedGroups = [];

      allGroups.forEach(group => {
        if (group.category) {
          if (!groupsByCategory[group.category]) {
            groupsByCategory[group.category] = [];
          }
          groupsByCategory[group.category].push(group);
        } else {
          uncategorizedGroups.push(group);
        }
      });

      // Combine categories with their groups
      const categoriesWithGroups = categoriesData.map(category => ({
        ...category,
        groups: groupsByCategory[category.id] || [],
        group_count: (groupsByCategory[category.id] || []).length,
        page_count: (groupsByCategory[category.id] || []).reduce((sum, g) => sum + (g.page_count || 0), 0),
        is_expanded: category.is_expanded !== false
      }));

      // Add uncategorized section if there are uncategorized groups
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

      // If no categories exist but there are groups, show them in uncategorized
      if (categoriesWithGroups.length === 0 && allGroups.length > 0) {
        categoriesWithGroups.push({
          id: 'uncategorized',
          name: '전체 그룹',
          icon: '📂',
          domain: domainId,
          groups: allGroups,
          group_count: allGroups.length,
          page_count: allGroups.reduce((sum, g) => sum + (g.page_count || 0), 0),
          is_expanded: true
        });
      }

      setCategories(categoriesWithGroups);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch categories:', err);
      setError('데이터를 불러오는데 실패했습니다.');
      setCategories([]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch pages for a specific group
  const fetchGroupPages = async (groupId) => {
    try {
      const response = await groupService.getGroupPages(groupId);
      const pages = Array.isArray(response.data?.results)
        ? response.data.results
        : Array.isArray(response.data)
          ? response.data
          : [];
      setGroupPages(prev => ({ ...prev, [groupId]: pages }));
    } catch (err) {
      console.error('Failed to fetch group pages:', err);
      setGroupPages(prev => ({ ...prev, [groupId]: [] }));
    }
  };

  // Toggle group expansion to show/hide pages
  const toggleGroupExpand = async (groupId) => {
    const isExpanded = expandedGroups[groupId];

    if (!isExpanded && !groupPages[groupId]) {
      // Fetch pages when expanding for the first time
      await fetchGroupPages(groupId);
    }

    setExpandedGroups(prev => ({
      ...prev,
      [groupId]: !prev[groupId]
    }));
  };

  // Handle group click to filter tree
  const handleGroupFilter = (group) => {
    if (onGroupFilter) {
      // If clicking the same group, clear the filter
      if (activeGroupFilter === group.id) {
        onGroupFilter(null);
      } else {
        onGroupFilter(group.id);
      }
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

  // Remove page from group
  const removePageFromGroup = async (pageId, groupId) => {
    try {
      setLoading(true);
      await pageService.assignGroup(pageId, null);
      // Refresh pages for this group
      await fetchGroupPages(groupId);
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error('Failed to remove page from group:', err);
      alert('페이지 제거 실패: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const deleteGroup = async (groupId, e) => {
    e.stopPropagation();
    const confirmed = window.confirm('이 그룹을 삭제하시겠습니까?');
    if (!confirmed) return;

    try {
      setLoading(true);
      await groupService.deleteGroup(groupId);

      // Clear filter if this group was filtered
      if (activeGroupFilter === groupId && onGroupFilter) {
        onGroupFilter(null);
      }

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
    setShowCreateCategoryForm(false);
    setShowCreateGroupForm(null);
    setNewCategory({ name: '', icon: '📁', description: '' });
    setNewGroup({ name: '', color: '#3B82F6', description: '' });
  };

  // Get total groups count
  const totalGroups = categories.reduce((sum, cat) => sum + (cat.groups?.length || 0), 0);

  if (loading && categories.length === 0) {
    return <div className="category-manager loading">로딩 중...</div>;
  }

  return (
    <div className="category-manager">
      <div className="category-manager-header">
        <h3>📁 그룹 관리</h3>
        <div className="header-actions">
          {activeGroupFilter && (
            <button
              className="btn-clear-filter"
              onClick={() => onGroupFilter && onGroupFilter(null)}
              title="필터 해제"
            >
              ✕ 필터 해제
            </button>
          )}
          {!showCreateCategoryForm && (
            <button
              className="btn-create-category"
              onClick={() => setShowCreateCategoryForm(true)}
              disabled={loading}
            >
              + 카테고리
            </button>
          )}
        </div>
      </div>

      {/* Summary */}
      <div className="group-summary">
        <span>총 {totalGroups}개 그룹</span>
        {activeGroupFilter && (
          <span className="filter-active">필터 적용 중</span>
        )}
      </div>

      {error && <div className="category-error">{error}</div>}

      {/* Quick Add Group (no category) */}
      {!showCreateCategoryForm && categories.length === 0 && (
        <div className="quick-add-section">
          <p className="empty-message">그룹을 생성하여 페이지를 분류하세요</p>
          <button
            className="btn-add-group-quick"
            onClick={() => setShowCreateGroupForm('uncategorized')}
          >
            + 새 그룹 만들기
          </button>
        </div>
      )}

      {/* Create Category Form */}
      {showCreateCategoryForm && (
        <div className="category-create-form">
          <h4>새 카테고리 만들기</h4>
          <div className="form-row">
            <input
              type="text"
              placeholder="아이콘"
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
                  {category.groups?.length || 0}그룹
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
                      <div key={group.id} className="group-item-expanded">
                        {/* Group Header - Clickable */}
                        <div
                          className={`group-header ${activeGroupFilter === group.id ? 'active-filter' : ''}`}
                          onClick={() => handleGroupFilter(group)}
                          title="클릭하여 이 그룹만 표시"
                        >
                          <button
                            className="group-expand-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleGroupExpand(group.id);
                            }}
                          >
                            {expandedGroups[group.id] ? '▼' : '▶'}
                          </button>
                          <div
                            className="group-color-dot"
                            style={{ backgroundColor: group.color }}
                          />
                          <span className="group-name">{group.name}</span>
                          <span className="group-page-count">
                            {group.page_count || 0}페이지
                          </span>
                          {activeGroupFilter === group.id && (
                            <span className="filter-badge">필터 중</span>
                          )}
                          <button
                            className="btn-delete-sm"
                            onClick={(e) => deleteGroup(group.id, e)}
                            title="그룹 삭제"
                          >
                            🗑️
                          </button>
                        </div>

                        {/* Pages in Group */}
                        {expandedGroups[group.id] && (
                          <div className="group-pages-list">
                            {groupPages[group.id] && groupPages[group.id].length > 0 ? (
                              groupPages[group.id].map((page) => (
                                <div key={page.id} className="page-item">
                                  <span className="page-icon">📄</span>
                                  <span className="page-label" title={page.url}>
                                    {page.custom_label || page.title || page.path || page.url}
                                  </span>
                                  {page.seo_score !== null && (
                                    <span className={`page-seo-score score-${page.seo_score >= 90 ? 'good' : page.seo_score >= 70 ? 'medium' : 'poor'}`}>
                                      {page.seo_score}
                                    </span>
                                  )}
                                  <button
                                    className="btn-remove-page"
                                    onClick={() => removePageFromGroup(page.id, group.id)}
                                    title="그룹에서 제거"
                                    disabled={loading}
                                  >
                                    ✕
                                  </button>
                                </div>
                              ))
                            ) : (
                              <div className="empty-pages">페이지가 없습니다</div>
                            )}
                          </div>
                        )}
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
                      onClick={() => {
                        setNewGroup(prev => ({ ...prev, color: getRandomGroupColor() }));
                        setShowCreateGroupForm(category.id);
                      }}
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
