import { render, screen } from '@testing-library/react';
import Page from './page';

describe('Home Page', () => {
  it('renders the Next.js logo', () => {
    render(<Page />);
    const logo = screen.getByAltText('Next.js logo');
    expect(logo).toBeInTheDocument();
  });

  it('renders the getting started text', () => {
    render(<Page />);
    const text = screen.getByText(/Get started by editing/);
    expect(text).toBeInTheDocument();
  });
});
