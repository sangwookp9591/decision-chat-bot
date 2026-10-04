import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ShortId, shortId } from './ShortId';

describe('shortId', () => {
  it('keeps the prefix and the last six characters of a long id', () => { expect(shortId('req_1b6d959edffd4e4e807ea8bc08bc8acd')).toBe('req_…bc8acd'); });
  it('passes short ids through', () => { expect(shortId('req_1')).toBe('req_1'); });
  it('does not invent a prefix for ids without one', () => { expect(shortId('0123456789abcdef0123')).toBe('…ef0123'); });
});
describe('<ShortId>', () => {
  it('shows the short form and keeps the full id for hover, copy and assistive tech', () => {
    const { container } = render(<ShortId id="req_1b6d959edffd4e4e807ea8bc08bc8acd" />);
    const chip = container.querySelector('.short-id')!;
    expect(screen.getByText('req_…bc8acd').getAttribute('aria-hidden')).toBe('true');
    expect(chip.getAttribute('title')).toBe('req_1b6d959edffd4e4e807ea8bc08bc8acd');
    expect(chip.textContent).toContain('req_1b6d959edffd4e4e807ea8bc08bc8acd');
  });
});
