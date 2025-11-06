<div align="center">
  <br />
    <a href="https://www.librai.tech">
      <img alt="LibrAI Logo" src="./assets/logo.plo" alt="LibrAI Logo" width="50%" height="auto">
    </a>
  <br />
</div>

# Loki: 一个开源的事实核查工具

## 概述
Loki 是我们的开源解决方案，旨在自动化事实核查的过程。它提供了一个全面的流程，用于将长文本分解为单个声明，评估其核查价值，生成证据搜索查询，抓取证据，并最终核查声明。该工具对记者、研究人员以及任何对信息真实性感兴趣的人尤其有用。要获取最新信息，请在[我们的网站](https://www.librai.tech/)订阅我们的新闻通讯或加入我们的 [Discord](https://discord.gg/ssxtFVbDdT)！

## 快速开始

### 克隆仓库并进入项目目录
```bash
git clone https://github.com/Libr-AI/OpenFactVerification.git
cd OpenFactVerification
```

### 使用 poetry 安装 (选项 1)
1. 遵循[安装指南](https://python-poetry.org/docs/)安装 Poetry。
2. 运行以下命令安装所有依赖项：
```bash
poetry install
```

### 使用 pip 安装 (选项 2)
1. 创建一个 Python 3.9 或更高版本的环境并激活它。
2. 进入项目目录并安装所需的包：
```bash
pip install -r requirements.txt
```

### 配置 API 密钥

您可以选择将必要的 API 密钥导出到环境中

- 示例：将必要的 API 密钥导出到环境中
```bash
export SERPER_API_KEY=... # 如果使用 serper 进行证据检索，则需要此项
export OPENAI_API_KEY=... # 所有任务都需要此项
```

或者，您可以通过 YAML 文件配置 API 密钥，更多详情请参阅[用户指南](docs/user_guide.md)。

一个示例测试用例：
<div align="center">
	<img src="./assets/cmd_example.gif" alt="drawing" width="80%"/>
</div>

## 用法

Loki 事实核查器的主要接口位于 `factcheck/__init__.py`，其中包含 `check_response` 方法。该方法集成了完整的事实核查流程，每个功能都封装在其各自的类中，如功能部分所述。

#### 作为库使用

```python
from factcheck import FactCheck

factcheck_instance = FactCheck()

# 示例文本
text = "Your text here"

# 运行事实核查流程
results = factcheck_instance.check_response(text)
print(results)
```

#### 作为 Web 应用使用
```bash
python webapp.py --api_config demo_data/api_config.yaml
```

#### 多模态用法

```bash
# 字符串
python -m factcheck --modal string --input "MBZUAI is the first AI university in the world"
# 文本
python -m factcheck --modal text --input demo_data/text.txt
# 语音
python -m factcheck --modal speech --input demo_data/speech.mp3
# 图像
python -m factcheck --modal image --input demo_data/image.webp
# 视频
python -m factcheck --modal video --input demo_data/video.m4v
```

#### 自定义您的体验
有关高级用法，请参阅我们的[用户指南](docs/user_guide.md)。

## [试用我们的在线服务](https://aip.librai.tech/login)

<!-- 💪 **加入我们的创新之旅，成为支持者版的一员** -->

随着我们不断发展和完善我们的事实核查解决方案，我们很高兴邀请您成为我们旅程中不可或缺的一部分。通过注册我们的支持者版，您不仅可以解锁一套高级功能和权益，还在为可信信息的未来提供动力。

以下是我们在线服务的截图。
[点击此处立即试用！](https://aip.librai.tech/login)

<div align="center">
	<img src="./assets/online_screenshot.png" alt="drawing" width="80%"/>
</div>

<!--
您的支持使我们能够：

🚀 持续创新：开发新的、前沿的功能，让您在对抗错误信息的斗争中保持领先。

💡 改进和完善：增强用户体验，使我们的应用不仅功能强大，而且使用愉快。

🌱 发展我们的社区：投资于我们社区茁壮成长和扩展所需的资源和工具。

🎁 作为我们感激之情的表示，立即注册即可获得**免费的代币积分**——这是我们对您的一点感谢，感谢您相信我们的使命并支持我们的成长！

<div align="center">

| 功能 | 开源版 | 支持者版 |
|----------------------------------------|:-------------------:|:------------------:|
| 可信的核查结果 | ✅ | ✅ |
| 来自开放网络的多样化证据 | ✅ | ✅ |
| 自动纠正错误信息 | ✅ | ✅ |
| 隐私和数据安全 | ✅ | ✅ |
| 多模态输入 | ✅ | ✅ |
| 一站式定制解决方案 | ❌ | ✅ |
| 可定制的核查数据源 | ❌ | ✅ |
| 增强的用户体验 | ❌ | ✅ |
| 更高的效率和准确性 | ❌ | ✅ |

</div> -->

## 为 Loki 项目做贡献

欢迎并感谢您对 Loki 项目的兴趣！我们欢迎社区的贡献和反馈。要开始，请参阅我们的[贡献指南](https://github.com/Libr-AI/OpenFactVerification/tree/main/docs/CONTRIBUTING.md)。

### 致谢
- 特别感谢所有为本项目做出贡献的贡献者。

<!---
在此处添加 slack 频道
-->

### 保持联系和了解情况

不要错过最新的更新、功能发布和社区见解！我们邀请您订阅我们的新闻通讯，成为我们不断壮大的社区的一员。

💌 立即在[我们的网站](https://www.librai.tech/)订阅！

## Star 历史

> [![Star History Chart](https://api.star-history.com/svg?repos=Libr-AI/OpenFactVerification&type=Date)](https://star-history.com/#Libr-AI/OpenFactVerification&Date)

## 引用
```
@misc{li2024lokiopensourcetoolfact,
      title={Loki: An Open-Source Tool for Fact Verification}, 
      author={Haonan Li and Xudong Han and Hao Wang and Yuxia Wang and Minghan Wang and Rui Xing and Yilin Geng and Zenan Zhai and Preslav Nakov and Timothy Baldwin},
      year={2024},
      eprint={2410.01794},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2410.01794}, 
}
```
# 事实核查
