import '@testing-library/jest-dom';
import { vi } from 'vitest';

console.log("Mocking Browser APIs in setup.ts...");

// Mock ResizeObserver
const ResizeObserverMock = vi.fn(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
}));

vi.stubGlobal('ResizeObserver', ResizeObserverMock);

// Mock matchMedia
vi.stubGlobal('matchMedia', vi.fn((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
})));

// Mock ScrollTo
vi.stubGlobal('scrollTo', vi.fn());

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

// Mock IntersectionObserver
const IntersectionObserverMock = vi.fn(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
}));
vi.stubGlobal('IntersectionObserver', IntersectionObserverMock);

// Mock PointerEvent
if (!global.PointerEvent) {
    vi.stubGlobal('PointerEvent', class PointerEvent extends Event { });
}
