import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import App from './App';
import React from 'react';

// Mock framer-motion to prevent JSDOM layout crashes
vi.mock('framer-motion', async () => {
    const actual = await vi.importActual("framer-motion")
    return {
        ...actual,
        AnimatePresence: ({ children }: any) => children,
        motion: new Proxy({}, {
            get: (_target, prop) => {
                return ({ children, ...props }: any) => {
                    // return React.createElement('div', props, children); // Simple
                    // But better to just return children in a fragment or div?
                    // Let's use a div
                    return React.createElement('div', props, children);
                }
            }
        })
    }
})


describe('App', () => {
    it('renders without crashing', () => {
        render(<App />);
        expect(document.body).toBeDefined();
    });
});
