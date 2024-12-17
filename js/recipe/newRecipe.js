import Database from "/js_classes/database.js";

export function newRecipe(db, params){
    const entries = params.entries()

    const recipe_cols = ['name', 'description','url','rating']
    const image_cols = ['image']
    const recipeTag_cols = ['recipe_id','tag_id']

    const recipe = {}
    const image = {}
    const tags = []

    for(const entry of entries) {
        console.log('entry',entry)
      if(Number.isInteger(parseInt(entry[0])) && Number.isInteger(parseInt(entry[1])))
        tags.push(entry[1])
      else if(recipe_cols.includes(entry[0]))
        recipe[entry[0]] = entry[1]
      else if(image_cols.includes(entry[0]) && image_cols[entry[0]]!=='')
        image[entry[0]] = entry[1]
    }

    console.log('insert recipe', Object.keys(recipe), Object.values(recipe))
    const id_recipe = db.insert('recipe', Object.keys(recipe), Object.values(recipe))
    console.log('id is ',id_recipe)
    for(const tag of tags){
        console.log('insert ',tag)
        db.insert('recipeTag', ['recipe_id', 'tag_id'], [id_recipe, tag])
    }

    if(image.image)
        db.insert('image', ['recipe_id', 'url', 'alt_text'], [id_recipe, image.image, image.alt_text || null])

    return ''
}