import { AppHeader } from './components/AppHeader';
import { Sidebar } from './components/Sidebar';
import { MobileNav } from './components/MobileNav';

export function AppLayout({ children }) {
  return (
    <div className="app">
      <AppHeader />
      <div className="app-body">
        <Sidebar />
        <main className="app-main">
          <div className="page">{children}</div>
        </main>
      </div>
      <MobileNav />
    </div>
  );
}

export default AppLayout;
