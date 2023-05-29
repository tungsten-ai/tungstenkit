import { createTheme, Typography } from "@mui/material";

import { TypographyOptions } from "@mui/material/styles/createTypography";

declare module "@mui/material/Typography" {
  interface TypographyPropsVariantOverrides {
    mainText: true;
    codeText:true;
    mainTextMedium:true,
    mainTextSmall:true
  }
}

interface ExtendedTypographyOptions extends TypographyOptions {
  mainText: React.CSSProperties;
}

const theme = createTheme({
  palette: {
    primary: {
      main: "#0f1f37",
    },
    secondary: {
      main: "#1976D2",
    },
    error: {
      main: "#d32f2f",
      pastel: "#e8cad2",
    },
    success: {
      main: "#2e7d32",
      pastel: "#c1e1c1",
    },
  },
  typography: {
    mainText: {
      fontFamily: `"Open Sans","Source Sans", "Helvetica", sans-serif`,
      fontSize: 16,
    },
    mainTextMedium: {
      fontFamily: `"Open Sans","Source Sans", "Helvetica", sans-serif`,
      fontSize: 14,
    },
    mainTextSmall: {
      fontFamily: `"Open Sans","Source Sans", "Helvetica", sans-serif`,
      fontSize: 12,
    }, 
    codeText:{
      fontFamily: `"monospace","Roboto", "Helvetica", sans-serif`,
      fontSize: 16,
    }
  } as ExtendedTypographyOptions,
  components: {
    MuiButtonBase: {
      defaultProps: {
        disableRipple: true,
      },
    },
  },
  body: {},
});

export default theme;
