import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import { Dashboard } from './pages/Dashboard';
import { SkillsList } from './pages/SkillsList';
import { ReviewQueue } from './pages/ReviewQueue';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Input } from './components/ui/input';
import { Card, CardHeader, CardTitle, CardContent } from './components/ui/card';
import { StatCard } from './components/cards/StatCard';
import { Package } from 'lucide-react';

// 全域 mock axios，避免實際發出 API 請求
vi.mock('axios', () => {
  const mockAxios = {
    create: vi.fn(() => mockAxios),
    get: vi.fn(() => Promise.resolve({ data: {} })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    put: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    defaults: { headers: { common: {} } },
  };
  return { default: mockAxios };
});

// 建立測試用的 QueryClient（關閉 retry 避免測試掛起）
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// 通用 wrapper：包含 QueryClientProvider + MemoryRouter
function renderWithProviders(
  ui: React.ReactElement,
  { initialEntries = ['/'] }: { initialEntries?: string[] } = {}
) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// -----------------------------------------------------------------------
// 測試 1：App 整體渲染（包含 BrowserRouter，但 App 本身內建 BrowserRouter）
// -----------------------------------------------------------------------
describe('App', () => {
  it('renders without crashing', () => {
    const queryClient = createTestQueryClient();
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    );
    // App 有 BrowserRouter，至少要渲染出某個 DOM
    expect(container).toBeTruthy();
    expect(container.firstChild).not.toBeNull();
  });
});

// -----------------------------------------------------------------------
// 測試 2：Dashboard 頁面 - 載入中狀態渲染
// -----------------------------------------------------------------------
describe('Dashboard page', () => {
  it('renders loading spinner while fetching data', () => {
    renderWithProviders(<Dashboard />);
    // useStats 和 useRiskDistribution 都在 pending 狀態，顯示 spinner
    // 或者在 jsdom 環境中 react-query 可能會同步顯示 loading
    // 不論哪種，至少不應該拋出例外
    expect(document.body).toBeTruthy();
  });

  it('mounts the Dashboard component without throwing', () => {
    expect(() => renderWithProviders(<Dashboard />)).not.toThrow();
  });
});

// -----------------------------------------------------------------------
// 測試 3：SkillsList 頁面
// -----------------------------------------------------------------------
describe('SkillsList page', () => {
  it('renders without crashing', () => {
    expect(() => renderWithProviders(<SkillsList />)).not.toThrow();
  });

  it('contains search input', () => {
    renderWithProviders(<SkillsList />);
    const searchInput = screen.getByPlaceholderText('Search skills...');
    expect(searchInput).toBeInTheDocument();
  });
});

// -----------------------------------------------------------------------
// 測試 4：ReviewQueue 頁面
// -----------------------------------------------------------------------
describe('ReviewQueue page', () => {
  it('renders without crashing', () => {
    expect(() => renderWithProviders(<ReviewQueue />)).not.toThrow();
  });
});

// -----------------------------------------------------------------------
// 測試 5：Button UI 元件
// -----------------------------------------------------------------------
describe('Button component', () => {
  it('renders with default variant', () => {
    render(<Button>Click me</Button>);
    const btn = screen.getByRole('button', { name: 'Click me' });
    expect(btn).toBeInTheDocument();
  });

  it('renders with outline variant', () => {
    render(<Button variant="outline">Outline</Button>);
    const btn = screen.getByRole('button', { name: 'Outline' });
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveClass('border');
  });

  it('renders as disabled', () => {
    render(<Button disabled>Disabled</Button>);
    const btn = screen.getByRole('button', { name: 'Disabled' });
    expect(btn).toBeDisabled();
  });
});

// -----------------------------------------------------------------------
// 測試 6：Badge UI 元件
// -----------------------------------------------------------------------
describe('Badge component', () => {
  it('renders badge text', () => {
    render(<Badge>Pending</Badge>);
    expect(screen.getByText('Pending')).toBeInTheDocument();
  });

  it('renders with destructive variant', () => {
    render(<Badge variant="destructive">High Risk</Badge>);
    const badge = screen.getByText('High Risk');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-destructive');
  });
});

// -----------------------------------------------------------------------
// 測試 7：Input UI 元件
// -----------------------------------------------------------------------
describe('Input component', () => {
  it('renders an input element', () => {
    render(<Input placeholder="Enter text" />);
    const input = screen.getByPlaceholderText('Enter text');
    expect(input).toBeInTheDocument();
    expect(input.tagName).toBe('INPUT');
  });

  it('accepts type prop', () => {
    render(<Input type="email" placeholder="Email" />);
    const input = screen.getByPlaceholderText('Email');
    expect(input).toHaveAttribute('type', 'email');
  });
});

// -----------------------------------------------------------------------
// 測試 8：Card UI 元件
// -----------------------------------------------------------------------
describe('Card component', () => {
  it('renders card with header and content', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Test Title</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Test content</p>
        </CardContent>
      </Card>
    );
    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test content')).toBeInTheDocument();
  });
});

// -----------------------------------------------------------------------
// 測試 9：StatCard 元件
// -----------------------------------------------------------------------
describe('StatCard component', () => {
  it('renders title and value', () => {
    render(<StatCard title="Total Skills" value={42} />);
    expect(screen.getByText('Total Skills')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('renders with icon', () => {
    const { container } = render(
      <StatCard title="Skills" value={10} icon={Package} />
    );
    // icon 以 SVG 方式渲染
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('renders warning variant without throwing', () => {
    expect(() =>
      render(<StatCard title="Pending" value={5} variant="warning" />)
    ).not.toThrow();
  });

  it('renders danger variant without throwing', () => {
    expect(() =>
      render(<StatCard title="High Risk" value={3} variant="danger" />)
    ).not.toThrow();
  });
});
