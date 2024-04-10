from nonebot import require
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_alconna")  # noqa

from typing import List, Optional
from nonebot import get_driver, on_command
from nonebot.params import CommandArg
from .crates import Crates
from .skins import Skins
from .utils import Utils
from .model import Crate, SelectedSkin, Config
from nonebot_plugin_alconna.uniseg import Image, UniMessage
from nonebot.adapters import Message, Event


__plugin_meta__ = PluginMetadata(
    name="CSGO开箱模拟器",
    description="nonebot的CS2/CSGO开箱模拟器",
    usage="输入 /open 开箱",
    type="application",
    config=Config,
    supported_adapters=None
)

crates = Crates()
skins = Skins()
utils = Utils()

userLastTime: dict = {}
groupLastTime: dict = {}
config = Config.parse_obj(get_driver().config)
user_cd = config.csgo_user_cd
group_cd = config.csgo_group_cd

crate_opening = on_command("open", aliases={"csgo开箱"}, priority=5)
list_cases = on_command("cases", aliases={"csgo武器箱列表"}, priority=5)
list_souvenir = on_command("svs", aliases={"csgo纪念包列表"}, priority=5)
search_skin = on_command("s_skin", aliases={"csgo皮肤搜索"}, priority=5)
open_until = on_command("openuntil", priority=5)


@list_cases.handle()
async def handle_list_cases():
    cases_list = crates.get_case_name_list()
    cases_list_img = utils.generate_case_list_img(cases_list)
    await list_cases.finish(await UniMessage(Image(raw=cases_list_img)).export())

    # cases_list_str = ""
    # for case in cases_list:
    #     cases_list_str += f"{case}\n"
    # await list_cases.finish(f"{cases_list_str}")


@list_souvenir.handle()
async def handle_list_souvenir():
    svs_list = crates.get_souvenir_name_list()
    cases_list_img = utils.generate_case_list_img(svs_list)
    await list_cases.finish(await UniMessage(Image(raw=cases_list_img)).export())

    # svs_list_str = ""
    # for sv in svs_list[0:len(svs_list) // 2]:
    #     svs_list_str += f"{sv}\n"
    # await list_souvenir.send(f"{svs_list_str}")
    # svs_list_str = ""
    # for sv in svs_list[len(svs_list)//2:]:
    #     svs_list_str += f"{sv}\n"
    # await list_souvenir.finish(f"{svs_list_str}")


@crate_opening.handle()
async def handle_open_crate(event: Event, args: Message = CommandArg()):
    (amount, name) = extract_args(args)
    if name:
        crate = get_crate(name)
        if crate:
            if not crate.contains:
                await crate_opening.finish("箱子里面是空的")

            # group_id = event.get_session_id()
            # if user_cd > 0 and event.sender.user_id in userLastTime and event.time - userLastTime[event.sender.user_id] < user_cd:
            #     leftTime = user_cd - \
            #         (event.time - userLastTime[event.sender.user_id])
            #     await crate_opening.finish(
            #         MessageSegment.reply(event.message_id) +
            #         f"开箱太快了，请等待{leftTime}秒"
            #     )

            # if group_cd > 0 and group_id in groupLastTime and event.time - groupLastTime[group_id] < group_cd:
            #     leftTime = group_cd - \
            #         (event.time - groupLastTime[group_id])
            #     await crate_opening.finish(
            #         MessageSegment.reply(event.message_id) +
            #         f"群开箱冷却中，请等待{leftTime}秒"
            #     )
            # userLastTime[event.sender.user_id] = event.time
            # groupLastTime[group_id] = event.time

            img_base64 = await utils.img_from_url(crate.image)
            await crate_opening.send(
                await UniMessage(Image(raw=img_base64)).export()
                + f"正在开启{amount}个{crate.name}..."
            )

            items = crates.open_crate_multiple(crate, amount)
            opened_skins: List[SelectedSkin] = []
            for item in items:
                opened_skins.append(skins.get_skins(item.name))

            image = await utils.merge_images(
                opened_skins, crate.name, crate.image, event.sender.nickname
            )
            await crate_opening.finish(await UniMessage(Image(raw=image)).export())
        else:
            await crate_opening.finish("箱子不存在")
    else:
        await crate_opening.finish("请输入箱子名称")


@search_skin.handle()
async def handle_search_skin(args: Message = CommandArg()):
    if skin_name := args.extract_plain_text().strip():
        found_skin_list = skins.search_skin(skin_name)
        if len(found_skin_list) == 0:
            await search_skin.finish("没找到捏")
        for skin in found_skin_list:
            img_base64 = await utils.img_from_url(skin.image)
            await search_skin.send(
                await UniMessage(Image(raw=img_base64)).export()
                + f"找到饰品{skin.name}"
            )
    else:
        await search_skin.finish("请输入皮肤名称")


@open_until.handle()
async def handle_open_until(args: Message = CommandArg()):
    name = args.extract_plain_text().strip()
    get_rare = False
    count = 0
    if name:
        crate = get_crate(name)
        if crate:
            if not crate.contains:
                await crate_opening.finish("箱子里面是空的")
            while not get_rare:
                items = crates.open_crate_multiple(crate, 200)
                if count and count % 200 == 0:
                    await crate_opening.send(f"已经开启{count}个{crate.name}...")
                for item in items:
                    count += 1
                    if "★" in item.name:
                        rare_item = item.name
                        get_rare = True
                        break

            await crate_opening.finish(
                f"共开启{count}个{crate.name}，开出隐秘物品:{rare_item}"
            )
        else:
            await crate_opening.finish("箱子不存在")
    else:
        await crate_opening.finish("请输入箱子名称")


def extract_args(args: Message = CommandArg()):
    arg_list = args.extract_plain_text().split(" ")
    if len(arg_list) > 0 and arg_list[0] != "":
        if len(arg_list) == 2:
            arg_amount = int(arg_list[0])
            amount = arg_amount if arg_amount < 20 else 20
            crate_name = arg_list[1]
        else:
            amount = 1
            crate_name = arg_list[0]
        return amount, crate_name
    else:
        return 1, None


def get_result_statistics(user: str, times: int, amount: int):
    return f"用户{user}开启{times}次{amount}个箱子"


def get_crate(name: str) -> Optional[Crate]:
    return crates.get_case_by_name(name) or crates.get_souvenir_by_name(name)
