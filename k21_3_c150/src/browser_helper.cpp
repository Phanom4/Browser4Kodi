#include "include/cef_app.h"

int main(int argc, char* argv[])
{
  CefMainArgs mainArgs(argc, argv);

  const int result = CefExecuteProcess(
      mainArgs,
      nullptr,
      nullptr
  );

  return result >= 0 ? result : 1;
}
