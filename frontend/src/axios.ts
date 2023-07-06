import axios from "axios";

export const getClientSideAxios = () => {
  const instance = axios.create({
    timeout: 3000,
  });
  return instance;
};
