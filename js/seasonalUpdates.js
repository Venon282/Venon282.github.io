export function ColorsUpdate(){
    const now = new Date()
    const day = now.getDate()
    const month = now.getMonth() // 0-11

    // Halloween colors
    if(month === 9){
        document.documentElement.style.setProperty('--home-url', "url('../asset/image/home/halloween.jpg')")

        document.documentElement.style.setProperty('--primary-dark'             , '#803B0C')
        document.documentElement.style.setProperty('--primary-medium-dark'      , '#CC5E13')
        document.documentElement.style.setProperty('--primary-medium-light'     , '#E6772D')
        document.documentElement.style.setProperty('--primary-light'            , '#FFAC74')
        document.documentElement.style.setProperty('--secondary-dark'           , '#0A0A08')
        document.documentElement.style.setProperty('--secondary-medium-dark'    , '#33342E')
        document.documentElement.style.setProperty('--secondary-medium-light'   , '#797A76')
        document.documentElement.style.setProperty('--secondary-light'          , '#BCBCBA')
    // Christmas colors
    }else if(month === 11 && day <= 25){
        document.documentElement.style.setProperty('--home-url', "url('../asset/image/home/christmas.jpg')")

        document.documentElement.style.setProperty('--primary-dark'             , '#00382a') //#0F3D16
        document.documentElement.style.setProperty('--primary-medium-dark'      , '#186123')
        document.documentElement.style.setProperty('--primary-medium-light'     , '#327A3D')
        document.documentElement.style.setProperty('--primary-light'            , '#84b58b') //#62A16B
        document.documentElement.style.setProperty('--secondary-dark'           , '#62080B')
        document.documentElement.style.setProperty('--secondary-medium-dark'    , '#9C0C12')
        document.documentElement.style.setProperty('--secondary-medium-light'   , '#B6262B')
        document.documentElement.style.setProperty('--secondary-light'          , '#f5a4a7') //#D5575C
    // New Year festive colors
    }else if(month === 11){
        document.documentElement.style.setProperty('--home-url', "url('../asset/image/home/new_year.jpg')")

        document.documentElement.style.setProperty('--primary-dark'             , '#1A0033') // Deep plum with a hint of purple
        document.documentElement.style.setProperty('--primary-medium-dark'      , '#3A0055') // Rich purple
        document.documentElement.style.setProperty('--primary-medium-light'     , '#6A0A88') // Vibrant magenta-purple
        document.documentElement.style.setProperty('--primary-light'            , '#E6C3FF') // Soft lavender
        document.documentElement.style.setProperty('--secondary-dark'           , '#2A0066') // Dark indigo
        document.documentElement.style.setProperty('--secondary-medium-dark'    , '#4D0099') // Bright royal purple
        document.documentElement.style.setProperty('--secondary-medium-light'   , '#7D3ADB') // Lighter violet with a glow
        document.documentElement.style.setProperty('--secondary-light'          , '#FFD8F0') // Pastel pink for accents
    }
}

export default function Updates(){
    ColorsUpdate()
}
