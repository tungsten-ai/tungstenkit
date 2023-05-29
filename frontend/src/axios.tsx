import axios from "axios";

export const getClientSideAxios = () => {
  const instance = axios.create({
    // baseURL: process.env.NEXT_PUBLIC_BASE_URL,
    timeout: 1000,
  });
  return instance;
};
