import React from 'react';
import CategoryItem from './CategoryItem';

function CategoryList({ categories }) {
  const sortedCategories = [...categories].sort((a, b) => a.score - b.score);

  return (
    <div className="category-list">
      <div className="category-list-header">
        <h2>Category Breakdown</h2>
        <p className="category-subtitle">Click any category to see details and evidence</p>
      </div>

      <div className="categories">
        {sortedCategories.map((category, index) => (
          <CategoryItem key={index} category={category} />
        ))}
      </div>

      <div className="category-legend">
        <div className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: '#22c55e' }}></span>
          <span>70-100: Good</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: '#f59e0b' }}></span>
          <span>40-69: Moderate</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: '#ef4444' }}></span>
          <span>0-39: Poor</span>
        </div>
      </div>
    </div>
  );
}

export default CategoryList;