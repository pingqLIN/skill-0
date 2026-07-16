import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AUTH_TOKEN_STORAGE_KEY } from '@/auth/storage';

const mocks = vi.hoisted(() => {
  const createInstance = () => ({
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  });
  const instances = [createInstance(), createInstance(), createInstance()];
  let index = 0;
  const create = vi.fn(() => instances[index++]);
  return { instances, create };
});

vi.mock('axios', () => ({
  default: { create: mocks.create },
}));

import { runtimeApi } from './client';

describe('authenticated Runtime client', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('uses the core Runtime base URL and injects the stored bearer token', () => {
    expect(mocks.create).toHaveBeenNthCalledWith(3, {
      baseURL: 'http://localhost:8000',
    });
    const runtimeInstance = runtimeApi as unknown as (typeof mocks.instances)[number];
    const requestInterceptor = runtimeInstance.interceptors.request.use.mock.calls[0][0];
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, 'runtime-token');

    const config = requestInterceptor({ headers: {} });
    expect(config.headers.Authorization).toBe('Bearer runtime-token');
  });

  it('clears the shared auth session after a Runtime 401', async () => {
    const runtimeInstance = runtimeApi as unknown as (typeof mocks.instances)[number];
    const responseError = runtimeInstance.interceptors.response.use.mock.calls[0][1];
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, 'expired-token');

    await expect(responseError({ response: { status: 401 } })).rejects.toEqual({
      response: { status: 401 },
    });
    expect(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull();
  });
});
