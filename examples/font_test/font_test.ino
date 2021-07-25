/********************************************************************
*
* tgx-font library example: displaying some text with a font.
*
* This example runs on a Teensy 4/4.1 and an ILI9341 screen.
*
* Required external libraries:
*
* - Screen driver [ILI9341_T4 library] : https://github.com/vindar/ILI9341_T4
* - 2D/3D graphic library [tgx] : https://github.com/vindar/tgx
*
********************************************************************/

// the sceen driver library
#include <ILI9341Driver.h>

// the graphic library
#include <tgx.h>

// the fonts we will use. 
// load the 'lite' versions to save space because 
// we only use characters in the range [32,126].
#include <font_Roboto_AA4_lite.h>
#include <font_HennyPenny_AA4_lite.h>
#include <font_PermanentMarker_AA4_lite.h>
#include <font_Hanalei_AA4_lite.h>
#include <font_SourceCodePro_AA4_lite.h>
#include <font_ZenTokyoZoo_AA4_lite.h>
#include <font_ShadowsIntoLight_AA4_lite.h>
#include <font_Pacifico_AA4_lite.h>

// screen size in portrait mode
#define LX  320
#define LY  240

// 20MHz SPI. 
#define SPI_SPEED    20000000

// set the pins: here for SPI0 on Teensy 4.0
// ***  Recall that DC must be on a valid cs pin !!! ***
#define PIN_SCK     13  // (needed) SCK pin for SPI0 on Teensy 4.0
#define PIN_MISO    12  // (needed) MISO pin for SPI0 on Teensy 4.0
#define PIN_MOSI    11  // (needed) MOSI pin for SPI0 on Teensy 4.0
#define PIN_DC      10  // (needed) CS pin for SPI0 on Teensy 4.0
#define PIN_RESET   6   // (needed) any pin can be used 
#define PIN_CS      9   // (needed) any pin can be used
#define PIN_BACKLIGHT  5    // only required if LED pin from screen is connected to Teensy 
#define PIN_TOUCH_IRQ 255 // 255 if touch not connected
#define PIN_TOUCH_CS  255 // 255 if touch not connected


// the screen driver object
ILI9341_T4::ILI9341Driver tft(PIN_CS, PIN_DC, PIN_SCK, PIN_MOSI, PIN_MISO, PIN_RESET, PIN_TOUCH_CS, PIN_TOUCH_IRQ);


// memory framebuffer...
tgx::RGB565 fb[LX * LY]; 

// ...and the associated Image object we will draw on. 
tgx::Image<tgx::RGB565> im(fb,LX,LY);


void setup()
{
    Serial.begin(9600);

    while (!tft.begin(SPI_SPEED))
        {
        Serial.println("Initialization error...");
        delay(1000);
        }

    tft.setRotation(3);                 // portrait mode 240 x320

    if (PIN_BACKLIGHT != 255)
        { // make sure backlight is on
        pinMode(PIN_BACKLIGHT, OUTPUT);
        digitalWrite(PIN_BACKLIGHT, HIGH);
        }

    im.fillScreen(tgx::RGB32_Yellow);
    im.drawText("The quick fox jumps over the lazy dog", tgx::iVec2(3, 20), tgx::RGB565_Black, font_Roboto_AA4_lite_18, true);
    im.drawText("The quick fox jumps over the lazy dog", tgx::iVec2(3, 50), tgx::RGB565_Black, font_HennyPenny_AA4_lite_18, true);
    im.drawText("The quick fox jumps over the lazy dog", tgx::iVec2(3, 80), tgx::RGB565_Black, font_PermanentMarker_AA4_lite_16, true);
    im.drawText("The quick fox jumps over the lazy dog", tgx::iVec2(3, 110), tgx::RGB565_Black, font_Hanalei_AA4_lite_18, true);
    im.drawText("The quick fox jumps over the lazy dog", tgx::iVec2(3, 140), tgx::RGB565_Black, font_SourceCodePro_AA4_lite_14, true);
    im.drawText("The quick fox jumps over the lazy dog", tgx::iVec2(3, 170), tgx::RGB565_Black, font_ZenTokyoZoo_AA4_lite_20, true);
    im.drawText("The quick fox jumps over the lazy dog", tgx::iVec2(3, 200), tgx::RGB565_Black, font_ShadowsIntoLight_AA4_lite_20, true);
    im.drawText("The quick fox jumps over the lazy dog", tgx::iVec2(3, 230), tgx::RGB565_Black, font_Pacifico_AA4_lite_18, true);

    tft.update((uint16_t*)im.data());

}


void loop()
    {
    }


/** end of file */
