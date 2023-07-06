import axios from "axios";

export const getClientSideAxios = () => {
  console.log(process.env)
  const instance = axios.create({
    timeout: 3000,
  });
  return instance;
};
