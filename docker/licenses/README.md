# 随 Somalier 二进制分发的依赖许可

这些文件不是 TAFFISH 对第三方代码的重新授权。仓库根 LICENSE 只描述打包代码；
Somalier 原始 MIT 文本仍由固定上游源码复制到镜像的 licenses/somalier/。

nim-dependencies/manifest.json 把全部 18 个锁定依赖绑定到 nimble.lock 的
版本、commit、官方源码 archive SHA256 和实际保留文件 SHA256。许可正文不改写；
为 Git 文本文件仅规范 LF 与末尾换行，原始文本 hash 和规范化说明也在 manifest 中。
源文件中的 miniz/stb 许可段单独保留，不把这些内嵌 C 组件当成 Nim wrapper 的同一许可。

Nimble 的安装目录会裁剪根 LICENSE，因此这些文本来自对应 commit 的原始源码，
不是安装后缺文件时凭包名补写。hileup 的实际 LICENSE 是 Apache-2.0，不能沿用旧文档
中的 MIT 误写。minizip 没有独立根 LICENSE；保留原始作者/MIT package metadata 和
miniz.c 中完整的原始许可段，不杜撰版权年份或作者声明。

duktape、untar 是锁定的间接构建依赖，但未进入本候选 Somalier 编译闭包；manifest
保留其来源与这个边界，不假装找到不存在的独立 LICENSE。构建期脚本核对实际编译闭包，
如果无保留声明的依赖以后进入二进制，将失败并要求重新审计。其它未使用的可选依赖
文本保守保留；文本存在不意味着镜像提供 GPU/OpenCL 等功能。

collect-nim-notices.py 从固定 Nim 2.2.4 builder 复制 copying.txt，并保留实际用到的
Nim 标准库源文件头部版权段，包括 Dragonbox/Schubfach。BOOST-1.0.txt 来自
https://www.boost.org/LICENSE_1_0.txt，SHA256 被运行期 checker 固定。
最终镜像的 /usr/share/doc 和 /usr/share/common-licenses 保留 Debian 运行包的
版权/许可文本与链接；不再把版权文件和普通缓存一起删除。

check-notices.py 在轻量 identity smoke 中离线校验依赖版本、许可库存/hash、实际
Nim 运行库声明，以及 HTSlib、OpenBLAS、Python 版权文件。这里只做交付文件保留与
可追溯性检查，不声称替代完整法律审查。
