
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import React from 'react';

const Simple = () => <div>Hello MediaLens</div>;

describe('Sanity Check', () => {
    it('renders basic component', () => {
        render(<Simple />);
        expect(screen.getByText('Hello MediaLens')).toBeInTheDocument();
    });
});
