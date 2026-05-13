import { Outlet, Link } from 'react-router-dom';

export function Layout() {
  return (
    <div style={{ fontFamily: 'sans-serif' }}>
      {/* Menu Superior Global */}
      <nav style={{ padding: '20px', background: '#2c3e50', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ margin: 0, fontSize: '24px' }}>🛡️ FraudOps Dashboard</h1>
        
        <div>
          <Link to="/" style={{ color: '#ecf0f1', marginRight: '20px', textDecoration: 'none', fontWeight: 'bold' }}>
            Painel de Workers
          </Link>
          <Link to="/revisions" style={{ color: '#ecf0f1', textDecoration: 'none', fontWeight: 'bold' }}>
            Todas as Revisões
          </Link>
        </div>
      </nav>

      {/* Conteúdo Dinâmico das Páginas */}
      <main style={{ padding: '30px', maxWidth: '1200px', margin: '0 auto' }}>
        <Outlet /> 
      </main>
    </div>
  );
}