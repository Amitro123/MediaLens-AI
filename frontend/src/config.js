// Frontend configuration
// DEV_MODE_ENABLED is true in development or when VITE_DEVLENS_DEV_MODE=true

export const DEV_MODE_ENABLED =
    import.meta.env.VITE_DEVLENS_DEV_MODE === "true" ||
    import.meta.env.MODE === "development";

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
