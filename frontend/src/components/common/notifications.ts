import { notifications } from "@mantine/notifications";

const NOTIFCATION_SX = {
  height: "3rem",
};

const showSuccessNotification = (message: string) =>
  notifications.show({
    message: `${message}`,
    color: "green",
    sx: NOTIFCATION_SX,
  });

const showFailureNotification = (message: string) =>
  notifications.show({
    message: `${message}`,
    color: "red",
    sx: NOTIFCATION_SX,
  });

export { showSuccessNotification, showFailureNotification };
