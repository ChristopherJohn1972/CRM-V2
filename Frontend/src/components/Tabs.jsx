import { cn } from '../utils/cn';

export function Tabs({ tabs, activeKey, onChange, className }) {
  return (
    <div className={cn('tabs', className)} role="tablist" aria-orientation="horizontal">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          role="tab"
          aria-selected={tab.key === activeKey}
          className={cn('tab', tab.key === activeKey && 'is-active')}
          onClick={() => onChange(tab.key)}
          aria-controls={`panel-${tab.key}`}
        >
          {tab.label}
          {typeof tab.count === 'number' && <span className="tab__count">({tab.count})</span>}
        </button>
      ))}
    </div>
  );
}

export default Tabs;