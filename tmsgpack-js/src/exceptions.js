export class TMsgpackError extends Error {
    constructor(message) {
        super(message);
        this.name = 'TMsgpackError';
    }
}

