export function logError(context, error, meta = {}) {
    const payload = {
        context,
        message: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : null,
        meta,
        timestamp: new Date().toISOString(),
    };

    console.error(`[${context}]`, payload);
}
