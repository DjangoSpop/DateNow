import { resolveApiBaseUrl } from '../src/config/env';

describe('resolveApiBaseUrl', () => {
  it('defaults to localhost in development, 10.0.2.2 on Android emulator', () => {
    expect(resolveApiBaseUrl({ configured: null, appEnv: 'development', platform: 'ios' })).toBe(
      'http://localhost:8000/api/v1',
    );
    expect(resolveApiBaseUrl({ configured: undefined, appEnv: 'development', platform: 'android' })).toBe(
      'http://10.0.2.2:8000/api/v1',
    );
  });

  it('appends /api/v1 once and strips trailing slashes', () => {
    expect(resolveApiBaseUrl({ configured: 'http://192.168.1.5:8000/', appEnv: 'development', platform: 'ios' })).toBe(
      'http://192.168.1.5:8000/api/v1',
    );
    expect(
      resolveApiBaseUrl({ configured: 'https://api.datenow.app/api/v1', appEnv: 'production', platform: 'ios' }),
    ).toBe('https://api.datenow.app/api/v1');
  });

  it('requires an https URL in production', () => {
    expect(() => resolveApiBaseUrl({ configured: null, appEnv: 'production', platform: 'ios' })).toThrow();
    expect(() =>
      resolveApiBaseUrl({ configured: 'http://api.datenow.app', appEnv: 'production', platform: 'ios' }),
    ).toThrow(/https/);
  });
});
